# -*- coding: utf-8 -*-
"""
Servidor local para a ferramenta de correcao.
Abre automaticamente o navegador e permite mover/excluir imagens diretamente.
Execute: python servidor.py
"""
import sys, os, json, shutil, subprocess, secrets, hashlib
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
from urllib.parse import urlparse, parse_qs, unquote
import threading, webbrowser

# ── Paths: Windows local ou Linux VPS (via variável de ambiente) ──
BANCO = Path(os.environ.get('ARTECROMO_BANCO', r"E:\Banco de Imagens"))
PORT  = int(os.environ.get('ARTECROMO_PORT', 8765))
DOMINIO = os.environ.get('ARTECROMO_DOMINIO', 'localhost')

# ── Configurações (carregadas de config.json) ─────────
def _carregar_config():
    cfg_path = BANCO / 'config.json'
    defaults = {'usuario': 'admin', 'senha': 'DEFINA_ARTECROMO_SENHA',
                'whatsapp': '5511987916193', 'nome_loja': 'Arte Cromo Estampas'}
    try:
        with open(str(cfg_path), encoding='utf-8') as f:
            dados = json.load(f)
        defaults.update(dados)
    except Exception:
        pass
    # Variáveis de ambiente têm prioridade (VPS usa .service)
    if os.environ.get('ARTECROMO_USUARIO'):
        defaults['usuario'] = os.environ['ARTECROMO_USUARIO']
    if os.environ.get('ARTECROMO_SENHA'):
        defaults['senha'] = os.environ['ARTECROMO_SENHA']
    return defaults

_cfg = _carregar_config()
LOGIN_USER  = _cfg['usuario']
LOGIN_SENHA = _cfg['senha']
# ──────────────────────────────────────────────────────
SESSOES = set()           # tokens válidos em memória
_LOGIN_TENTATIVAS = {}    # IP → (contagem, ultimo_timestamp) para rate limit
_MAX_TENTATIVAS  = 5      # bloqueia após 5 falhas
_JANELA_SEG      = 300    # janela de 5 minutos

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BANCO), **kwargs)

    def log_message(self, format, *args):
        pass  # silenciar logs

    def do_GET(self):
        # Redirecionar raiz para login
        if self.path in ('/', ''):
            self.send_response(302)
            self.send_header('Location', '/login.html')
            self.end_headers()
            return
        # API config (protegida por token)
        if self.path == '/api/config':
            if not self._token_valido():
                self._nao_autorizado(); return
            cfg = _carregar_config()
            safe = {'usuario': cfg.get('usuario','admin'),
                    'whatsapp': cfg.get('whatsapp',''),
                    'nome_loja': cfg.get('nome_loja','')}
            resposta = json.dumps(safe).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.send_header('Content-Length', len(resposta))
            self.end_headers()
            self.wfile.write(resposta)
            return
        super().do_GET()

    def do_POST(self):
        if self.path == '/api/login':
            self.fazer_login()
        elif self.path == '/api/logout':
            self.fazer_logout()
        elif self.path == '/baixar-pdf':
            self.baixar_pdf()
        elif self.path in ('/mover', '/atualizar', '/rotacionar', '/salvar-ordem',
                           '/upload', '/desfazer', '/renomear', '/criar-categoria',
                           '/converter-cmyk', '/api/salvar-config'):
            if not self._token_valido():
                self._nao_autorizado()
                return
            if self.path == '/mover':
                self.processar(self.ler_body())
            elif self.path == '/atualizar':
                self.atualizar()
            elif self.path == '/rotacionar':
                self.rotacionar(self.ler_body())
            elif self.path == '/salvar-ordem':
                self.salvar_ordem(self.ler_body())
            elif self.path == '/upload':
                self.upload_arquivo()
            elif self.path == '/desfazer':
                self.desfazer(self.ler_body())
            elif self.path == '/renomear':
                self.renomear_arquivo(self.ler_body())
            elif self.path == '/criar-categoria':
                self.criar_categoria(self.ler_body())
            elif self.path == '/converter-cmyk':
                self.converter_cmyk()
            elif self.path == '/baixar-pdf':
                self.baixar_pdf()
            elif self.path == '/api/salvar-config':
                self.salvar_config(self.ler_body())
        else:
            self.send_error(404)

    def _ip(self):
        return self.headers.get('X-Forwarded-For', self.client_address[0]).split(',')[0].strip()

    def _token_valido(self):
        token = self.headers.get('X-Token', '')
        return token in SESSOES

    def _nao_autorizado(self):
        resposta = json.dumps({'ok': False, 'erro': 'Não autorizado'}).encode('utf-8')
        self.send_response(401)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(resposta))
        self.end_headers()
        self.wfile.write(resposta)

    def fazer_login(self):
        import time
        ip  = self._ip()
        now = time.time()
        # Rate limit
        cnt, ts = _LOGIN_TENTATIVAS.get(ip, (0, 0))
        if now - ts > _JANELA_SEG:
            cnt = 0  # reset janela
        if cnt >= _MAX_TENTATIVAS:
            resposta = json.dumps({'ok': False, 'erro': 'Muitas tentativas. Aguarde 5 minutos.'}).encode('utf-8')
            self.send_response(429)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', len(resposta))
            self.end_headers()
            self.wfile.write(resposta)
            return

        dados = self.ler_body()
        user  = dados.get('usuario', '')
        senha = dados.get('senha', '')
        if user == LOGIN_USER and senha == LOGIN_SENHA:
            _LOGIN_TENTATIVAS[ip] = (0, now)
            token = secrets.token_hex(32)
            SESSOES.add(token)
            resposta = json.dumps({'ok': True, 'token': token}).encode('utf-8')
        else:
            _LOGIN_TENTATIVAS[ip] = (cnt + 1, now)
            resposta = json.dumps({'ok': False, 'erro': 'Usuário ou senha incorretos'}).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(resposta))
        self.end_headers()
        self.wfile.write(resposta)

    def fazer_logout(self):
        dados = self.ler_body()
        token = dados.get('token', '')
        SESSOES.discard(token)
        resposta = json.dumps({'ok': True}).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(resposta))
        self.end_headers()
        self.wfile.write(resposta)

    def salvar_config(self, dados):
        global LOGIN_USER, LOGIN_SENHA
        try:
            cfg_path = BANCO / 'config.json'
            # Ler config atual
            try:
                with open(str(cfg_path), encoding='utf-8') as f:
                    cfg = json.load(f)
            except Exception:
                cfg = {}

            # Atualizar campos enviados
            if dados.get('usuario','').strip():
                cfg['usuario'] = dados['usuario'].strip()
            if dados.get('nome_loja','').strip():
                cfg['nome_loja'] = dados['nome_loja'].strip()
            if dados.get('whatsapp','').strip():
                # Limpar formatação — manter só dígitos
                wpp = ''.join(c for c in dados['whatsapp'] if c.isdigit())
                cfg['whatsapp'] = wpp

            # Senha: requer senha_atual correta
            senha_nova    = dados.get('senha_nova','').strip()
            senha_atual   = dados.get('senha_atual','').strip()
            senha_confirm = dados.get('senha_confirm','').strip()
            if senha_nova:
                if senha_atual != LOGIN_SENHA:
                    resposta = json.dumps({'ok': False, 'erro': 'Senha atual incorreta'}).encode('utf-8')
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', len(resposta))
                    self.end_headers()
                    self.wfile.write(resposta)
                    return
                if senha_nova != senha_confirm:
                    resposta = json.dumps({'ok': False, 'erro': 'A nova senha e a confirmação não coincidem'}).encode('utf-8')
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', len(resposta))
                    self.end_headers()
                    self.wfile.write(resposta)
                    return
                if len(senha_nova) < 6:
                    resposta = json.dumps({'ok': False, 'erro': 'Senha deve ter no mínimo 6 caracteres'}).encode('utf-8')
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', len(resposta))
                    self.end_headers()
                    self.wfile.write(resposta)
                    return
                cfg['senha'] = senha_nova
                LOGIN_SENHA = senha_nova

            # Salvar config.json
            with open(str(cfg_path), 'w', encoding='utf-8') as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
            try:
                os.chmod(str(cfg_path), 0o600)  # só root lê
            except Exception:
                pass

            # Atualizar variáveis em memória
            LOGIN_USER = cfg.get('usuario', LOGIN_USER)

            resposta = json.dumps({'ok': True}).encode('utf-8')
        except Exception as e:
            resposta = json.dumps({'ok': False, 'erro': str(e)}).encode('utf-8')

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(resposta))
        self.end_headers()
        self.wfile.write(resposta)

    def atualizar(self):
        try:
            py = sys.executable
            null = 'nul' if os.name == 'nt' else '/dev/null'

            def _rodar(script):
                os.system(f'"{py}" "{BANCO / script}" > {null} 2>&1')

            def _bg_delayed(script, delay=0):
                """Roda script após delay (segundos) para não competir com I/O."""
                caminho = str(BANCO / script)
                def _run():
                    if delay: __import__('time').sleep(delay)
                    if os.name == 'nt':
                        os.system(f'start /B "" "{py}" "{caminho}"')
                    else:
                        os.system(f'nohup "{py}" "{caminho}" > /dev/null 2>&1 &')
                threading.Thread(target=_run, daemon=True).start()

            # ── Sequência síncrona (rápida, ~30s) ─────────────
            _rodar('gerar_thumbs.py')
            # gerar_lista.py só roda no Windows (local).
            # Na VPS (Linux) o JSON é gerenciado pelo PC — não sobrescrever!
            if os.name == 'nt':
                _rodar('gerar_lista.py')
            _rodar('montar_catalogo.py')
            _rodar('atualizar_produtos_html.py')

            # ── Background com delay para não travar o servidor ─
            _bg_delayed('otimizar_web.py', delay=30)   # 30s depois
            _bg_delayed('gerar_pdf.py',    delay=120)  # 2 min depois

            resposta = json.dumps({'ok': True}).encode('utf-8')
        except Exception as e:
            resposta = json.dumps({'ok': False, 'erro': str(e)}).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(resposta))
        self.end_headers()
        self.wfile.write(resposta)

    def rotacionar(self, dados):
        from PIL import Image, ImageOps
        img_rel = dados.get('img', '')
        graus   = int(dados.get('graus', 90))
        THUMB_SIZE = (300, 300)

        def girar_arquivo(caminho, graus, como_thumb=False):
            ext = caminho.suffix.lower()
            img = Image.open(str(caminho))
            # Aplica rotação EXIF primeiro para neutralizar orientação original
            img = ImageOps.exif_transpose(img)
            # Converte para RGB puro — elimina qualquer dado EXIF residual
            img = img.convert("RGB")
            img = img.rotate(-graus, expand=True)
            if como_thumb:
                img.thumbnail(THUMB_SIZE, Image.LANCZOS)
                canvas = Image.new("RGB", THUMB_SIZE, (17, 17, 17))
                offset = ((THUMB_SIZE[0] - img.width) // 2, (THUMB_SIZE[1] - img.height) // 2)
                canvas.paste(img, offset)
                # Salva sem EXIF (exif=b'' garante que orientação não volta)
                canvas.save(str(caminho), "JPEG", quality=72, optimize=True, exif=b'')
            else:
                qualidade = 95 if ext in ['.jpg', '.jpeg'] else None
                if qualidade:
                    # Salva sem EXIF para evitar que browser aplique rotação antiga
                    img.save(str(caminho), "JPEG", quality=qualidade, optimize=True, exif=b'')
                else:
                    img.save(str(caminho))

        try:
            # Tenta img_web primeiro (VPS), depois img original (Windows local)
            img_web_rel = dados.get('img_web', '')
            candidatos = []
            if img_web_rel:
                candidatos.append(BANCO / unquote(img_web_rel).replace('/', os.sep))
            candidatos.append(BANCO / unquote(img_rel).replace('/', os.sep))

            caminho = next((p for p in candidatos if p.exists()), None)
            if caminho is None:
                raise FileNotFoundError(f'Imagem não encontrada: {img_rel}')

            girar_arquivo(caminho, graus, como_thumb=False)

            thumb_rel = dados.get('thumb', '')
            if thumb_rel and thumb_rel != img_rel:
                thumb_path = BANCO / unquote(thumb_rel).replace('/', os.sep)
                if thumb_path.exists():
                    girar_arquivo(thumb_path, graus, como_thumb=True)

            resposta = json.dumps({'ok': True}).encode('utf-8')
        except Exception as e:
            resposta = json.dumps({'ok': False, 'erro': str(e)}).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(resposta))
        self.end_headers()
        self.wfile.write(resposta)

    def upload_arquivo(self):
        from PIL import Image, ImageOps
        import io, re

        filename  = unquote(self.headers.get('X-Filename', 'imagem.jpg'))
        content_length = int(self.headers.get('Content-Length', 0))
        data = self.rfile.read(content_length)

        # Sanitizar nome do arquivo
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)

        # Salvar em Lancamentos/JPG/
        dest_dir = BANCO / 'Lançamentos' / 'JPG'
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / filename
        # Resolver conflito de nome
        if dest.exists():
            stem, suf = Path(filename).stem, Path(filename).suffix
            i = 1
            while dest.exists():
                dest = dest_dir / f"{stem}_{i}{suf}"
                i += 1

        with open(str(dest), 'wb') as f:
            f.write(data)

        # Gerar thumbnail
        THUMB_SIZE = (300, 300)
        thumb_dir = dest_dir / '_thumbs'
        thumb_dir.mkdir(exist_ok=True)
        thumb_path = thumb_dir / (dest.stem + '.jpg')
        try:
            img = Image.open(io.BytesIO(data))
            img = ImageOps.exif_transpose(img).convert('RGB')
            img.thumbnail(THUMB_SIZE, Image.LANCZOS)
            canvas = Image.new('RGB', THUMB_SIZE, (17, 17, 17))
            offset = ((THUMB_SIZE[0]-img.width)//2, (THUMB_SIZE[1]-img.height)//2)
            canvas.paste(img, offset)
            canvas.save(str(thumb_path), 'JPEG', quality=72, optimize=True)
        except:
            thumb_path = dest

        img_rel   = str(dest.relative_to(BANCO)).replace('\\', '/')
        thumb_rel = str(thumb_path.relative_to(BANCO)).replace('\\', '/')

        # Tentar classificar com CLIP (opcional)
        sugestao = ''
        try:
            sugestao = self._classificar_clip(data)
        except:
            pass

        # Se classificou, copiar para a categoria correta tambem
        if sugestao:
            try:
                cat_dir = BANCO / sugestao.replace(' › ', os.sep) / 'JPG'
                cat_dir.mkdir(parents=True, exist_ok=True)
                dst2 = cat_dir / dest.name
                if not dst2.exists():
                    shutil.copy2(str(dest), str(dst2))
                # Thumb da copia
                cat_thumb_dir = cat_dir / '_thumbs'
                cat_thumb_dir.mkdir(exist_ok=True)
                shutil.copy2(str(thumb_path), str(cat_thumb_dir / thumb_path.name))
            except:
                sugestao = ''

        # Adicionar ao JSON no inicio (posicao 0)
        json_path = BANCO / 'lista_imagens.json'
        try:
            with open(str(json_path), encoding='utf-8') as f:
                lista = json.load(f)
        except:
            lista = []

        novo_id = max((p['id'] for p in lista), default=0) + 1
        novo = {
            'id':    novo_id,
            'nome':  dest.stem,
            'cat':   'Lançamentos',
            'img':   img_rel,
            'thumb': thumb_rel,
        }
        if sugestao:
            novo['sugestao'] = sugestao

        lista.insert(0, novo)

        with open(str(json_path), 'w', encoding='utf-8') as f:
            json.dump(lista, f, ensure_ascii=False, indent=2)

        resposta = json.dumps({
            'ok': True, 'id': novo_id,
            'nome': dest.stem, 'sugestao': sugestao,
            'img': img_rel, 'thumb': thumb_rel
        }).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(resposta))
        self.end_headers()
        self.wfile.write(resposta)

    def _classificar_clip(self, data):
        """Tenta classificar a imagem com CLIP. Retorna nome da categoria ou vazio."""
        import io, torch
        from PIL import Image
        from transformers import CLIPProcessor, CLIPModel
        MODEL_DIR = "E:/clip_model"
        if not Path(MODEL_DIR).exists():
            return ''
        CATEGORIAS = {
            "Abstrato":            ["abstract art","geometric shapes","colorful pattern","digital art"],
            "Alimentos":           ["food","meal","fruit","vegetable","dish","drink"],
            "Animais › Leão":      ["lion","lions","lion portrait"],
            "Animais › Cavalos":   ["horse","horses","equestrian"],
            "Animais › Outros Animais": ["dog","cat","bird","animal","wildlife"],
            "Datas Comemorativas": ["christmas","birthday","new year","celebration","holiday"],
            "Esportes":            ["sport","football","soccer","basketball","athlete"],
            "Mulheres":            ["woman","girl","female model","beautiful woman"],
            "Natureza › Flores":   ["flowers","floral","bouquet","rose","garden"],
            "Natureza › Paisagem": ["landscape","mountain","river","ocean","waterfall"],
            "Natureza › Árvores":  ["tree","forest","jungle","woods"],
            "Old Money":           ["luxury","elegant mansion","yacht","classic car","aristocratic"],
            "Pessoas":             ["person","people","man","portrait","family"],
            "Religioso":           ["jesus christ","church","cross","prayer","angel","bible"],
            "Veículos › Carros":   ["car","sports car","automobile","truck"],
            "Veículos › Motos":    ["motorcycle","motorbike"],
        }
        model = CLIPModel.from_pretrained(MODEL_DIR)
        proc  = CLIPProcessor.from_pretrained(MODEL_DIR)
        model.eval()
        img = Image.open(io.BytesIO(data)).convert('RGB')
        textos = [(cat, kw) for cat, kws in CATEGORIAS.items() for kw in kws]
        cats = [c for c,_ in textos]
        txts = [t for _,t in textos]
        with torch.no_grad():
            inp = proc(text=txts, images=img, return_tensors='pt', padding=True, truncation=True)
            out = model(**inp)
            sims = out.logits_per_image.squeeze(0).softmax(dim=0)
        sc = {cat: sims[[i for i,c in enumerate(cats) if c==cat]].mean().item() for cat in CATEGORIAS}
        best = max(sc, key=sc.get)
        return best if sc[best] > 0.05 else ''

    def salvar_ordem(self, dados):
        try:
            json_path = BANCO / 'lista_imagens.json'
            with open(str(json_path), encoding='utf-8') as f:
                lista = json.load(f)
            # Atualiza a ordem da categoria recebida
            ordem = dados.get('ordem', [])  # lista de ids na nova ordem
            cat   = dados.get('cat', '')
            # Separa os itens da categoria e os demais
            outros = [p for p in lista if p['cat'] != cat]
            desta  = {p['id']: p for p in lista if p['cat'] == cat}
            reordenados = [desta[i] for i in ordem if i in desta]
            with open(str(json_path), 'w', encoding='utf-8') as f:
                json.dump(outros + reordenados, f, ensure_ascii=False, indent=2)
            resposta = json.dumps({'ok': True}).encode('utf-8')
        except Exception as e:
            resposta = json.dumps({'ok': False, 'erro': str(e)}).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(resposta))
        self.end_headers()
        self.wfile.write(resposta)

    def ler_body(self):
        tamanho = int(self.headers.get('Content-Length', 0))
        corpo = self.rfile.read(tamanho)
        return json.loads(corpo.decode('utf-8'))

    def processar(self, dados):
        acao    = dados.get('acao')          # 'mover' ou 'excluir'
        imgs    = dados.get('imgs', [])      # lista de {img, thumb}
        destino = dados.get('destino', '_Excluidos')

        movidos = 0
        erros   = []

        def _mover_arquivo(src, dst_dir, sufixo=''):
            """Move src para dst_dir, resolve conflito de nome."""
            if not src.exists():
                return None
            dst_dir.mkdir(parents=True, exist_ok=True)
            dst = dst_dir / (src.stem + sufixo + src.suffix)
            if dst.exists():
                i = 1
                while True:
                    dst = dst_dir / f"{src.stem}{sufixo}_{i}{src.suffix}"
                    if not dst.exists(): break
                    i += 1
            shutil.move(str(src), str(dst))
            return dst

        # Carregar JSON para atualizar no Linux (VPS)
        json_path = BANCO / 'lista_imagens.json'
        lista_json = []
        if os.name != 'nt':
            try:
                with open(str(json_path), encoding='utf-8') as f:
                    lista_json = json.load(f)
            except Exception:
                pass

        imgs_movidas = set()  # {img_rel} das imagens processadas com sucesso

        for item in imgs:
            img_rel = unquote(item.get('img', ''))
            try:
                src_img = BANCO / img_rel.replace('/', os.sep)
                fmt = img_rel.split('/')[-2] if img_rel.count('/') >= 2 else 'JPG'

                if acao == 'excluir':
                    dst_dir = BANCO / '_Excluidos'
                else:
                    dst_dir = BANCO / destino.replace(' › ', os.sep) / fmt

                # Mover imagem original (pode não existir na VPS — ok)
                resultado = _mover_arquivo(src_img, dst_dir)
                if resultado:
                    movidos += 1
                else:
                    # Na VPS o original não existe, mas ainda processa thumb/_web
                    movidos += 1

                # Mover thumb
                thumb_rel = unquote(item.get('thumb', ''))
                if thumb_rel and thumb_rel != img_rel:
                    src_thumb = BANCO / thumb_rel.replace('/', os.sep)
                    if acao == 'excluir':
                        _mover_arquivo(src_thumb, BANCO / '_Excluidos')
                    else:
                        _mover_arquivo(src_thumb, dst_dir / '_thumbs')

                # Mover _web (busca no JSON ou deriva do caminho)
                img_web_rel = ''
                if lista_json:
                    entry = next((p for p in lista_json if p.get('img') == img_rel), None)
                    if entry:
                        img_web_rel = entry.get('img_web', '')
                if not img_web_rel and img_rel:
                    # Derivar: Abstrato/JPG/007.jpg → Abstrato/JPG/_web/007.jpg
                    parts = img_rel.rsplit('/', 1)
                    if len(parts) == 2:
                        img_web_rel = parts[0] + '/_web/' + parts[1]

                if img_web_rel:
                    src_web = BANCO / img_web_rel.replace('/', os.sep)
                    if acao == 'excluir':
                        _mover_arquivo(src_web, BANCO / '_Excluidos')
                    else:
                        _mover_arquivo(src_web, dst_dir / '_web')

                imgs_movidas.add(img_rel)

            except Exception as e:
                erros.append(f"{img_rel}: {e}")

        # ── Atualizar lista_imagens.json ──────────────────────────
        if os.name == 'nt':
            # Windows: regenerar do disco
            try:
                py = sys.executable
                os.system(f'python "{BANCO / "gerar_lista.py"}" > nul 2>&1')
            except:
                pass
        else:
            # VPS/Linux: atualizar JSON diretamente (nunca rodar gerar_lista.py)
            if lista_json and imgs_movidas:
                try:
                    if acao == 'excluir':
                        lista_json = [p for p in lista_json
                                      if p.get('img', '') not in imgs_movidas]
                    else:
                        dest_path = destino.replace(' › ', '/')
                        for p in lista_json:
                            if p.get('img', '') not in imgs_movidas:
                                continue
                            nome = p['img'].split('/')[-1]
                            fmt  = p['img'].split('/')[-2] if p['img'].count('/') >= 2 else 'JPG'
                            p['cat']     = destino
                            p['img']     = f"{dest_path}/{fmt}/{nome}"
                            p['thumb']   = f"{dest_path}/{fmt}/_thumbs/{nome}"
                            p['img_web'] = f"{dest_path}/{fmt}/_web/{nome}"

                    with open(str(json_path), 'w', encoding='utf-8') as f:
                        json.dump(lista_json, f, ensure_ascii=False, indent=2)
                    try:
                        os.chmod(str(json_path), 0o644)
                    except Exception:
                        pass
                    # Regenerar catálogo HTML em background
                    py = sys.executable
                    null = '/dev/null'
                    def _regen():
                        import time; time.sleep(1)
                        os.system(f'ARTECROMO_BANCO="{BANCO}" "{py}" "{BANCO / "montar_catalogo.py"}" > {null} 2>&1')
                    threading.Thread(target=_regen, daemon=True).start()
                except Exception as e:
                    erros.append(f"JSON update: {e}")

        resposta = json.dumps({
            'ok': True,
            'movidos': movidos,
            'erros': erros
        }).encode('utf-8')

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(resposta))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(resposta)

    def desfazer(self, dados):
        try:
            estado = dados.get('estado', [])
            json_path = BANCO / 'lista_imagens.json'
            with open(str(json_path), 'w', encoding='utf-8') as f:
                json.dump(estado, f, ensure_ascii=False, indent=2)
            resposta = json.dumps({'ok': True}).encode('utf-8')
        except Exception as e:
            resposta = json.dumps({'ok': False, 'erro': str(e)}).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(resposta))
        self.end_headers()
        self.wfile.write(resposta)

    def renomear_arquivo(self, dados):
        from PIL import Image, ImageOps
        try:
            img_rel   = unquote(dados.get('img', '')).replace('/', os.sep)
            thumb_rel = unquote(dados.get('thumb', '')).replace('/', os.sep)
            novo_nome = dados.get('novo_nome', '').strip()
            if not novo_nome:
                raise ValueError('Nome vazio')

            img_path   = BANCO / img_rel
            thumb_path = BANCO / thumb_rel if thumb_rel else None

            # Novo caminho da imagem
            nova_img_path = img_path.parent / (novo_nome + img_path.suffix)
            if nova_img_path.exists() and nova_img_path != img_path:
                raise ValueError('Já existe um arquivo com esse nome')
            if img_path.exists():
                img_path.rename(nova_img_path)

            # Novo caminho da thumb
            novo_thumb_path = None
            if thumb_path and thumb_path.exists():
                novo_thumb_path = thumb_path.parent / (novo_nome + '.jpg')
                if novo_thumb_path != thumb_path:
                    thumb_path.rename(novo_thumb_path)

            # Atualizar no JSON
            nova_img_rel   = str(nova_img_path.relative_to(BANCO)).replace('\\', '/')
            novo_thumb_rel = str(novo_thumb_path.relative_to(BANCO)).replace('\\', '/') if novo_thumb_path else nova_img_rel

            json_path = BANCO / 'lista_imagens.json'
            with open(str(json_path), encoding='utf-8') as f:
                lista = json.load(f)
            for p in lista:
                if unquote(p.get('img', '')).replace('/', os.sep) == img_rel:
                    p['nome'] = novo_nome
                    p['img']  = nova_img_rel
                    p['thumb'] = novo_thumb_rel
                    break
            with open(str(json_path), 'w', encoding='utf-8') as f:
                json.dump(lista, f, ensure_ascii=False, indent=2)

            resposta = json.dumps({'ok': True, 'nova_img': nova_img_rel, 'novo_thumb': novo_thumb_rel}).encode('utf-8')
        except Exception as e:
            resposta = json.dumps({'ok': False, 'erro': str(e)}).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(resposta))
        self.end_headers()
        self.wfile.write(resposta)

    def criar_categoria(self, dados):
        try:
            nome = dados.get('nome', '').strip()
            if not nome:
                raise ValueError('Nome vazio')
            # Cria pasta e subpastas
            cat_dir = BANCO / nome.replace(' › ', os.sep)
            jpg_dir = cat_dir / 'JPG'
            thumb_dir = jpg_dir / '_thumbs'
            jpg_dir.mkdir(parents=True, exist_ok=True)
            thumb_dir.mkdir(parents=True, exist_ok=True)
            # Adicionar ao JSON se ainda não existir
            json_path = BANCO / 'lista_imagens.json'
            try:
                with open(str(json_path), encoding='utf-8') as f:
                    lista = json.load(f)
            except:
                lista = []
            # Não adiciona duplicatas — a categoria fica vazia (sem itens)
            with open(str(json_path), 'w', encoding='utf-8') as f:
                json.dump(lista, f, ensure_ascii=False, indent=2)
            resposta = json.dumps({'ok': True}).encode('utf-8')
        except Exception as e:
            resposta = json.dumps({'ok': False, 'erro': str(e)}).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(resposta))
        self.end_headers()
        self.wfile.write(resposta)

    def baixar_pdf(self):
        """Serve o PDF do catálogo para download."""
        pdf_path = BANCO / 'catalogo_arte_cromo.pdf'
        if not pdf_path.exists():
            resposta = json.dumps({'ok': False, 'erro': 'PDF não gerado ainda. Clique em Atualizar Catálogo primeiro.'}).encode('utf-8')
            self.send_response(404)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', len(resposta))
            self.end_headers()
            self.wfile.write(resposta)
            return
        with open(str(pdf_path), 'rb') as f:
            data = f.read()
        self.send_response(200)
        self.send_header('Content-Type', 'application/pdf')
        self.send_header('Content-Disposition', 'attachment; filename="Catalogo_Arte_Cromo.pdf"')
        self.send_header('Content-Length', len(data))
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(data)

    def converter_cmyk(self):
        try:
            from PIL import Image, ImageOps
            convertidos = 0
            erros = 0
            EXTENSOES = {'.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp', '.webp'}
            SKIP = {'PSD','CDR','PDF','__PYCACHE__','ARQUIVOS DE TRABALHO','_DUPLICATAS','_EXCLUIDOS'}
            for dirpath, dirs, files in os.walk(BANCO):
                dirs[:] = [d for d in dirs if d.upper() not in SKIP and not d.startswith('__')]
                for fname in files:
                    ext = Path(fname).suffix.lower()
                    if ext not in EXTENSOES:
                        continue
                    fpath = Path(dirpath) / fname
                    try:
                        with Image.open(fpath) as img:
                            modo = img.mode
                        if modo not in ('CMYK', 'CMYK;I'):
                            continue
                        img = Image.open(fpath)
                        img = ImageOps.exif_transpose(img).convert('RGB')
                        if ext in ('.tif', '.tiff', '.bmp'):
                            novo = fpath.with_suffix('.jpg')
                            img.save(str(novo), 'JPEG', quality=95, optimize=True, exif=b'')
                            fpath.unlink()
                        else:
                            img.save(str(fpath), 'JPEG', quality=95, optimize=True, exif=b'')
                        convertidos += 1
                    except Exception:
                        erros += 1
            # Regenerar lista e thumbs depois (gerar_lista só no Windows)
            py = sys.executable
            null = 'nul' if os.name == 'nt' else '/dev/null'
            os.system(f'"{py}" "{BANCO / "gerar_thumbs.py"}" > {null} 2>&1')
            if os.name == 'nt':
                os.system(f'"{py}" "{BANCO / "gerar_lista.py"}" > {null} 2>&1')
            os.system(f'"{py}" "{BANCO / "montar_catalogo.py"}" > {null} 2>&1')
            os.system(f'"{py}" "{BANCO / "atualizar_produtos_html.py"}" > nul 2>&1')
            resposta = json.dumps({'ok': True, 'convertidos': convertidos, 'erros': erros}).encode('utf-8')
        except Exception as e:
            resposta = json.dumps({'ok': False, 'erro': str(e)}).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(resposta))
        self.end_headers()
        self.wfile.write(resposta)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def end_headers(self):
        # CORS — restrito ao próprio servidor (ajustar domínio na produção)
        origin = self.headers.get('Origin', '')
        dominios_ok = {
            'http://localhost:8765',
            f'https://{DOMINIO}', f'http://{DOMINIO}',
            f'https://www.{DOMINIO}', f'http://www.{DOMINIO}',
        }
        if origin in dominios_ok:
            self.send_header('Access-Control-Allow-Origin', origin)
        else:
            self.send_header('Access-Control-Allow-Origin', f'https://{DOMINIO}')
        # Cache: imagens 7 dias, resto sem cache
        path = self.path.split('?')[0].lower()
        img_ext = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')
        if any(path.endswith(e) for e in img_ext):
            self.send_header('Cache-Control', 'public, max-age=604800')
        else:
            self.send_header('Cache-Control', 'no-cache, must-revalidate')
            self.send_header('Pragma', 'no-cache')
        # Headers de segurança
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'SAMEORIGIN')
        self.send_header('Referrer-Policy', 'strict-origin-when-cross-origin')
        super().end_headers()

def iniciar():
    os.chdir(str(BANCO))
    ThreadingHTTPServer.allow_reuse_address = True
    httpd = ThreadingHTTPServer(('', PORT), Handler)
    url = f'http://localhost:{PORT}/correcao_manual.html'
    print(f"\nServidor rodando em: http://localhost:{PORT}")
    print(f"Abrindo: {url}")
    print("Pressione Ctrl+C para parar.\n")
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    httpd.serve_forever()

if __name__ == '__main__':
    while True:
        try:
            iniciar()
        except KeyboardInterrupt:
            print("\nServidor encerrado.")
            break
        except Exception as e:
            print(f"Erro: {e} — reiniciando em 3s...")
            import time; time.sleep(3)
