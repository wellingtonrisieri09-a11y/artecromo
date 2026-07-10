# -*- coding: utf-8 -*-
"""
postar_instagram.py — posta 1 imagem por dia no Instagram da Arte Cromo.

Usa a API oficial da Meta (Instagram Graph API). Roda por cron, 1x/dia.

- Credenciais ficam em instagram_config.json (ig_user_id + token) — NAO vai pro git.
- Escolhe a proxima imagem ainda nao postada, na ordem do catalogo.
- Gera versao "pronta pro Instagram": 1080x1350 (4:5) fundo branco, centralizada.
- Publica com legenda: numero da estampa + link do site + hashtags.
- Marca como postada em instagram_postados.json (quando acaba, recomeca).

Teste sem postar:  python postar_instagram.py --dry
"""
import os, sys, json, urllib.request, urllib.parse
from pathlib import Path
from PIL import Image, ImageOps

BANCO  = Path(os.environ.get('ARTECROMO_BANCO', '/var/www/artecromo'))
SITE   = os.environ.get('ARTECROMO_SITE', 'https://srv1716345.hstgr.cloud')
JSON   = BANCO / 'lista_imagens.json'
CONFIG = BANCO / 'instagram_config.json'
ESTADO = BANCO / 'instagram_postados.json'
IG_DIR = BANCO / '_instagram'
API_VER = 'v21.0'


def carregar(p, default):
    try:
        with open(p, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default


def url_publica(rel):
    return SITE + '/' + '/'.join(urllib.parse.quote(s) for s in rel.split('/'))


def preparar_imagem(rel_path, num):
    """1080x1350 (4:5), fundo branco, imagem centralizada. Retorna caminho relativo publico."""
    src = BANCO / rel_path.replace('/', os.sep)
    IG_DIR.mkdir(exist_ok=True)
    im = Image.open(str(src))
    im = ImageOps.exif_transpose(im).convert('RGB')
    W, H = 1080, 1350
    im.thumbnail((W - 90, H - 90), Image.LANCZOS)
    canvas = Image.new('RGB', (W, H), (255, 255, 255))
    canvas.paste(im, ((W - im.width) // 2, (H - im.height) // 2))
    out = IG_DIR / f'post_{num}.jpg'
    canvas.save(str(out), 'JPEG', quality=88, optimize=True)
    try:
        os.chmod(str(out), 0o644)
    except Exception:
        pass
    return f'_instagram/post_{num}.jpg'


def api_post(url, params):
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r)


def publicar(ig_user, token, image_url, legenda):
    base = f'https://graph.facebook.com/{API_VER}'
    c = api_post(f'{base}/{ig_user}/media',
                 {'image_url': image_url, 'caption': legenda, 'access_token': token})
    cid = c['id']
    return api_post(f'{base}/{ig_user}/media_publish',
                    {'creation_id': cid, 'access_token': token})


def main():
    dry = '--dry' in sys.argv
    lista = carregar(JSON, [])
    if not lista:
        print('Sem imagens no catalogo.'); return

    postados = set(carregar(ESTADO, {}).get('ids', []))
    prox = next((p for p in lista if p.get('id') not in postados), None)
    if prox is None:
        print('Todas ja foram postadas — recomecando do inicio.')
        postados = set()
        prox = lista[0]

    num = str(lista.index(prox) + 1).zfill(4)
    ig_rel = preparar_imagem(prox.get('img_web') or prox['img'], num)
    image_url = url_publica(ig_rel)
    legenda = (
        f"Estampa nº {num} — Arte Cromo\n"
        f"Gostou? Faça seu pedido pelo WhatsApp!\n"
        f"Catálogo completo: {SITE}\n\n"
        f"#artecromo #estampas #gravuras #quadros #quadrosdecorativos #decoração"
    )

    print(f'Proxima: #{num}  {prox.get("cat")}  ->  {image_url}')
    if dry:
        print('----- LEGENDA -----')
        print(legenda)
        print('[DRY] Nada foi postado (modo teste).')
        return

    cfg = carregar(CONFIG, {})
    ig_user, token = cfg.get('ig_user_id'), cfg.get('token')
    if not ig_user or not token:
        print('ERRO: instagram_config.json ainda sem ig_user_id/token. Configure a conta primeiro.')
        return

    r = publicar(ig_user, token, image_url, legenda)
    print('Postado no Instagram:', r)
    postados.add(prox.get('id'))
    with open(ESTADO, 'w', encoding='utf-8') as f:
        json.dump({'ids': list(postados)}, f, ensure_ascii=False)
    print(f'OK! Marcada como postada. Total ja postado: {len(postados)}/{len(lista)}')


if __name__ == '__main__':
    main()
