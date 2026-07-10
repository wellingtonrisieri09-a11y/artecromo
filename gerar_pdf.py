# -*- coding: utf-8 -*-
"""
Catalogo Arte Cromo — PDF
- Fundo branco nas imagens
- Numeracao abaixo de cada imagem
- Nome da categoria no topo de cada pagina
"""
import json, sys, os, io
from pathlib import Path
from collections import OrderedDict
from fpdf import FPDF
from PIL import Image as PilImage

sys.stdout.reconfigure(encoding='utf-8')
PilImage.MAX_IMAGE_PIXELS = None

BANCO    = Path(os.environ.get('ARTECROMO_BANCO', r"E:\Banco de Imagens"))
SAIDA    = BANCO / "catalogo_arte_cromo.pdf"
JSON     = BANCO / "lista_imagens.json"

WHATSAPP = "(11) 94785-2675 / (11) 98791-6193"
WEBSITE  = "www.artecromoestampas.com.br"
EMAIL    = "arte.cromo@yahoo.com.br"

# Fontes: Windows ou Linux
if os.name == 'nt':
    FONT_DIR = Path(r"C:\Windows\Fonts")
    FONT_R   = str(FONT_DIR / "arial.ttf")
    FONT_B   = str(FONT_DIR / "arialbd.ttf")
    FONT_I   = str(FONT_DIR / "ariali.ttf")
else:
    # Ubuntu/Debian: apt-get install fonts-liberation
    FONT_DIR = Path("/usr/share/fonts/truetype/liberation")
    FONT_R   = str(FONT_DIR / "LiberationSans-Regular.ttf")
    FONT_B   = str(FONT_DIR / "LiberationSans-Bold.ttf")
    FONT_I   = str(FONT_DIR / "LiberationSans-Italic.ttf")

# ── Layout A4 ─────────────────────────────────────────
PG_W     = 210.0
PG_H     = 297.0
MARGEM   = 9.0
HEADER_H = 20.0      # altura do topo (logo)
FOOTER_H = 10.0      # altura do rodapé
CAT_H    = 14.0      # altura do nome da categoria no topo do grid
COLS     = 4
LINHAS   = 4          # 4 linhas (mais espaço por imagem)

# Área de grid (começa após header + categoria)
GRID_Y0  = HEADER_H + MARGEM + CAT_H   # onde começa o grid de imagens
GRID_H   = PG_H - GRID_Y0 - FOOTER_H - MARGEM
CELL_W   = (PG_W - 2 * MARGEM) / COLS
CELL_H   = GRID_H / LINHAS
NUM_H    = 10.0       # espaço reservado para número abaixo da imagem
IMG_AREA = CELL_H - NUM_H - 2   # altura disponível para a imagem

# ── Cores ──────────────────────────────────────────────
PRETO   = (0,   0,   0)
BRANCO  = (255, 255, 255)
VERDE   = (37,  211, 102)
VERDE_E = (20,  150, 60)
CINZA1  = (30,  30,  30)
CINZA2  = (80,  80,  80)
CINZA3  = (150, 150, 150)
CINZA4  = (220, 220, 220)

# ── Categoria atual da página ─────────────────────────
_cat_atual = ['']


class CatalogoPDF(FPDF):
    def header(self):
        # Faixa preta no topo
        self.set_fill_color(*CINZA1)
        self.rect(0, 0, PG_W, HEADER_H, 'F')
        self.set_draw_color(*VERDE)
        self.set_line_width(0.7)
        self.line(0, HEADER_H, PG_W, HEADER_H)

        # Nome Arte Cromo
        self.set_font('Arial', 'B', 15)
        self.set_text_color(*BRANCO)
        self.set_xy(MARGEM, 3)
        self.cell(65, 7, 'Arte Cromo', border=0)
        self.set_font('Arial', '', 9)
        self.set_text_color(*CINZA3)
        self.set_xy(MARGEM + 49, 5)
        self.cell(25, 5, 'ESTAMPAS', border=0)

        # Contato
        self.set_font('Arial', '', 8)
        self.set_text_color(*CINZA3)
        self.set_xy(110, 3)
        self.cell(PG_W - 110 - MARGEM, 5, 'WhatsApp: ' + WHATSAPP, border=0, align='R')
        self.set_xy(110, 10)
        self.cell(PG_W - 110 - MARGEM, 5, EMAIL, border=0, align='R')

        # Número da página
        self.set_font('Arial', '', 7)
        self.set_text_color(*CINZA3)
        self.set_xy(MARGEM, 13)
        self.cell(PG_W - 2*MARGEM, 5, f'Pagina {self.page_no()}', border=0, align='R')

        # Nome da categoria no topo do grid (abaixo do header)
        cat = _cat_atual[0]
        if cat:
            self.set_fill_color(*VERDE)
            self.rect(0, HEADER_H, PG_W, CAT_H, 'F')
            self.set_font('Arial', 'B', 11)
            self.set_text_color(*PRETO)
            self.set_xy(MARGEM, HEADER_H + 2)
            self.cell(PG_W - 2*MARGEM, CAT_H - 4, cat.upper(), border=0, align='C')

    def footer(self):
        self.set_y(-FOOTER_H)
        self.set_fill_color(*CINZA1)
        self.rect(0, PG_H - FOOTER_H, PG_W, FOOTER_H, 'F')
        self.set_draw_color(*VERDE)
        self.set_line_width(0.4)
        self.line(0, PG_H - FOOTER_H, PG_W, PG_H - FOOTER_H)
        self.set_font('Arial', '', 8)
        self.set_text_color(*CINZA3)
        self.set_y(PG_H - FOOTER_H + 1.5)
        self.cell(PG_W, 5, WEBSITE + '  |  ' + WHATSAPP, border=0, align='C')

    def card(self, p, col, linha):
        x = MARGEM + col * CELL_W + 1.5
        y = GRID_Y0 + linha * CELL_H

        card_w = CELL_W - 3
        card_h = CELL_H - 2

        # Fundo BRANCO com borda cinza clara
        self.set_fill_color(*BRANCO)
        self.set_draw_color(*CINZA4)
        self.set_line_width(0.2)
        self.rect(x, y, card_w, card_h, 'FD')

        # Área da imagem
        iw = card_w - 4
        ix = x + 2
        iy = y + 2

        img_bytes = None
        img_w_px = img_h_px = 1
        thumb   = BANCO / p['thumb'].replace('/', os.sep)
        orig    = BANCO / p['img'].replace('/', os.sep)
        img_web = BANCO / p.get('img_web', p['img']).replace('/', os.sep)
        for c in [thumb, img_web, orig]:
            if c.exists():
                try:
                    with PilImage.open(str(c)) as im:
                        im = im.convert('RGB')
                        im.thumbnail((300, 300), PilImage.LANCZOS)
                        img_w_px, img_h_px = im.size
                        buf = io.BytesIO()
                        im.save(buf, 'JPEG', quality=78, optimize=True)
                        buf.seek(0)
                        img_bytes = buf
                    break
                except Exception:
                    continue

        if img_bytes:
            try:
                ratio = img_w_px / img_h_px if img_h_px > 0 else 1
                if ratio >= 1:
                    dw = iw; dh = iw / ratio
                else:
                    dh = IMG_AREA; dw = IMG_AREA * ratio
                # Garantir que não ultrapasse a área
                if dw > iw: dw = iw; dh = dw / ratio
                if dh > IMG_AREA: dh = IMG_AREA; dw = dh * ratio
                cx = ix + (iw - dw) / 2
                cy = iy + (IMG_AREA - dh) / 2
                self.image(img_bytes, cx, cy, dw, dh, type='JPEG')
            except Exception:
                pass

        # Linha separadora fina acima do número
        sep_y = y + 2 + IMG_AREA + 1
        self.set_draw_color(*CINZA4)
        self.set_line_width(0.15)
        self.line(x + 1, sep_y, x + card_w - 1, sep_y)

        # Número em destaque — ABAIXO da imagem, dentro da faixa reservada
        num = str(p.get('seq', p['id'])).zfill(4)
        self.set_font('Arial', 'B', 10)
        self.set_text_color(*VERDE_E)
        self.set_xy(x, sep_y + 1)
        self.cell(card_w, NUM_H - 3, num, border=0, align='C')


# ── Carregar dados ────────────────────────────────────
print("Carregando dados...")
with open(str(JSON), encoding='utf-8') as f:
    lista = json.load(f)
lista = [p for p in lista if p['cat'] != '_Excluidos']
for i, p in enumerate(lista):
    p['seq'] = i + 1

por_cat = OrderedDict()
for p in lista:
    c = p['cat']
    if c not in por_cat:
        por_cat[c] = []
    por_cat[c].append(p)
cats = list(por_cat.keys())
print(f"Total: {len(lista)} imagens em {len(cats)} categorias")

# ── Criar PDF ─────────────────────────────────────────
pdf = CatalogoPDF(orientation='P', unit='mm', format='A4')
pdf.set_auto_page_break(False)
pdf.set_margins(MARGEM, HEADER_H, MARGEM)
pdf.add_font('Arial', '',  FONT_R)
pdf.add_font('Arial', 'B', FONT_B)
pdf.add_font('Arial', 'I', FONT_I)

# ── Capa — mesmo padrão visual do catálogo digital ───
_cat_atual[0] = ''
pdf.add_page()

# Fundo preto total
pdf.set_fill_color(*CINZA1)
pdf.rect(0, 0, PG_W, PG_H, 'F')

# ── Logo central (réplica do catálogo) ───────────────
logo_y = 90   # posição vertical do logo

# Barras CMYK — esquerda: cinza, ciano, amarelo, magenta (de cima p/ baixo)
cmyk_esq = [(136,136,136), (0,188,212), (245,230,66), (233,30,140)]
cmyk_dir = [(233,30,140), (245,230,66), (0,188,212), (136,136,136)]
bar_w, bar_h, bar_gap = 8, 8, 2
bars_total_h = len(cmyk_esq) * bar_h + (len(cmyk_esq)-1) * bar_gap

# Calcular posição X para centralizar [barras | texto | barras]
texto_w = 68
espaco  = 6
total_w = bar_w + espaco + texto_w + espaco + bar_w
start_x = (PG_W - total_w) / 2

# Barras esquerda
for i, cor in enumerate(cmyk_esq):
    pdf.set_fill_color(*cor)
    pdf.rect(start_x, logo_y + i*(bar_h+bar_gap), bar_w, bar_h, 'F')

# Barras direita
for i, cor in enumerate(cmyk_dir):
    pdf.set_fill_color(*cor)
    pdf.rect(start_x + bar_w + espaco + texto_w + espaco, logo_y + i*(bar_h+bar_gap), bar_w, bar_h, 'F')

# Texto "Arte Cromo"
pdf.set_font('Arial', 'B', 26)
pdf.set_text_color(*BRANCO)
pdf.set_xy(start_x + bar_w + espaco, logo_y - 2)
pdf.cell(texto_w, 18, 'Arte Cromo', border=0, align='C')

# "ESTAMPAS"
pdf.set_font('Arial', '', 9)
pdf.set_text_color(*CINZA3)
pdf.set_xy(start_x + bar_w + espaco, logo_y + 16)
pdf.cell(texto_w, 6, 'E S T A M P A S', border=0, align='C')

# Slogan
pdf.set_font('Arial', '', 8)
pdf.set_text_color(68, 68, 68)
pdf.set_xy(0, logo_y + bars_total_h + 8)
pdf.cell(PG_W, 6, 'Solucoes Graficas  .  Catalogo Digital', border=0, align='C')

# Linha verde separadora
pdf.set_draw_color(*VERDE)
pdf.set_line_width(1.2)
pdf.line(PG_W/2 - 55, logo_y + bars_total_h + 18, PG_W/2 + 55, logo_y + bars_total_h + 18)

# Informações abaixo
pdf.set_font('Arial', 'B', 12)
pdf.set_text_color(*VERDE)
pdf.set_xy(0, logo_y + bars_total_h + 24)
pdf.cell(PG_W, 8, f'Catalogo Digital  -  {len(lista)} imagens', border=0, align='C')

pdf.set_font('Arial', '', 9)
pdf.set_text_color(*CINZA3)
for txt, dy in [
    (f'{len(cats)} categorias', 36),
    ('', 46),
    ('Para fazer seu pedido:', 56),
    ('informe o numero da imagem pelo WhatsApp', 64),
    ('', 74),
    ('WhatsApp: ' + WHATSAPP, 82),
    (WEBSITE, 90),
    (EMAIL, 98),
]:
    pdf.set_xy(0, logo_y + bars_total_h + dy - 18)
    pdf.cell(PG_W, 7, txt, border=0, align='C')

# ── Páginas de imagens ────────────────────────────────
POR_PAG = COLS * LINHAS  # 16

total = 0
for cat in cats:
    imgs   = por_cat[cat]
    pagina = 0

    for i_pag in range(0, len(imgs), POR_PAG):
        bloco = imgs[i_pag : i_pag + POR_PAG]
        pagina += 1

        # Nova página para cada bloco — categoria sempre no topo
        _cat_atual[0] = cat
        pdf.set_fill_color(250, 250, 250)
        pdf.add_page()
        pdf.rect(0, GRID_Y0, PG_W, PG_H - GRID_Y0 - FOOTER_H, 'F')

        # Desenhar cards
        for idx, p in enumerate(bloco):
            col   = idx % COLS
            linha = idx // COLS
            pdf.card(p, col, linha)
            total += 1

        if total % 100 == 0:
            print(f"  {total}/{len(lista)} imagens geradas...")

print(f"  {total}/{len(lista)} imagens geradas...")

# Salvar em arquivo temporário e depois substituir atomicamente
import tempfile, shutil
tmp_fd, tmp_path = tempfile.mkstemp(suffix='.pdf', dir=str(BANCO))
try:
    os.close(tmp_fd)
    pdf.output(tmp_path)
    # Substituir o PDF final
    try:
        if SAIDA.exists():
            SAIDA.unlink()
    except Exception:
        pass
    shutil.move(tmp_path, str(SAIDA))
    # Garantir permissão de leitura pública (necessário no Linux/VPS)
    try:
        os.chmod(str(SAIDA), 0o644)
    except Exception:
        pass
    size_mb = SAIDA.stat().st_size / 1024 / 1024
    print(f"\nPDF gerado : {SAIDA}")
    print(f"Tamanho    : {size_mb:.1f} MB")
    print(f"Paginas    : {pdf.page}")
    print("OK!")
except Exception as e:
    try:
        os.unlink(tmp_path)
    except Exception:
        pass
    raise e
