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

WHATSAPP = "(11) 98791-6193"
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
# Cores da marca (CMYK — igual o site)
CIANO   = (0,   180, 230)
MAGENTA = (236, 10,  140)
AMARELO = (255, 207, 0)
CIANO_E = (0,   125, 170)

def faixa_cmyk(pdf, x, y, w, h):
    """Faixa tricolor ciano/magenta/amarelo (a mesma do site)."""
    seg = w / 3.0
    for i, cor in enumerate([CIANO, MAGENTA, AMARELO]):
        pdf.set_fill_color(*cor)
        pdf.rect(x + i*seg, y, seg, h, 'F')

# ── Categoria atual da página ─────────────────────────
_cat_atual = ['']


class CatalogoPDF(FPDF):
    def header(self):
        if self.page_no() == 1:
            return  # capa não leva cabeçalho
        # Faixa branca no topo com o logo oficial
        self.set_fill_color(*BRANCO)
        self.rect(0, 0, PG_W, HEADER_H, 'F')
        logo = str(BANCO / 'logo.png')
        if os.path.exists(logo):
            self.image(logo, MARGEM, 2.5, 0, HEADER_H - 5)

        # Contato (texto escuro, à direita)
        self.set_font('Arial', 'B', 8)
        self.set_text_color(*CINZA2)
        self.set_xy(105, 3.5)
        self.cell(PG_W - 105 - MARGEM, 4.5, 'WhatsApp: ' + WHATSAPP, border=0, align='R')
        self.set_font('Arial', '', 8)
        self.set_text_color(*CINZA3)
        self.set_xy(105, 8)
        self.cell(PG_W - 105 - MARGEM, 4.5, EMAIL, border=0, align='R')
        self.set_font('Arial', '', 7)
        self.set_xy(105, 12.5)
        self.cell(PG_W - 105 - MARGEM, 4.5, f'Pagina {self.page_no()}', border=0, align='R')

        # Faixa CMYK na base do cabeçalho
        faixa_cmyk(self, 0, HEADER_H - 1.6, PG_W, 1.6)

        # Nome da categoria no topo do grid (faixa ciano)
        cat = _cat_atual[0]
        if cat:
            self.set_fill_color(*CIANO)
            self.rect(0, HEADER_H, PG_W, CAT_H, 'F')
            self.set_font('Arial', 'B', 11)
            self.set_text_color(*PRETO)
            self.set_xy(MARGEM, HEADER_H + 2)
            self.cell(PG_W - 2*MARGEM, CAT_H - 4, cat.upper(), border=0, align='C')

    def footer(self):
        if self.page_no() == 1:
            return  # capa não leva rodapé
        self.set_y(-FOOTER_H)
        self.set_fill_color(*CINZA1)
        self.rect(0, PG_H - FOOTER_H, PG_W, FOOTER_H, 'F')
        faixa_cmyk(self, 0, PG_H - FOOTER_H, PG_W, 1.3)
        self.set_font('Arial', '', 8)
        self.set_text_color(*CINZA3)
        self.set_y(PG_H - FOOTER_H + 3)
        self.cell(PG_W, 5, WEBSITE + '   |   WhatsApp ' + WHATSAPP, border=0, align='C')

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
        self.set_text_color(*CIANO_E)
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

# Fundo escuro total
pdf.set_fill_color(*CINZA1)
pdf.rect(0, 0, PG_W, PG_H, 'F')

# ── Painel branco com o logo oficial (padrão do site) ──
panel_w, panel_h = 140, 118
panel_x = (PG_W - panel_w) / 2
panel_y = 44
pdf.set_fill_color(*BRANCO)
pdf.rect(panel_x, panel_y, panel_w, panel_h, 'F')
logo_size = 96
logo_path = str(BANCO / 'logo.png')
if os.path.exists(logo_path):
    pdf.image(logo_path, (PG_W - logo_size) / 2, panel_y + (panel_h - logo_size) / 2, logo_size, logo_size)

# Faixa CMYK sob o painel
faixa_cmyk(pdf, panel_x, panel_y + panel_h, panel_w, 5)

# ── Informações ────────────────────────────────────────
info_y = panel_y + panel_h + 22
pdf.set_font('Arial', 'B', 14)
pdf.set_text_color(*CIANO)
pdf.set_xy(0, info_y)
pdf.cell(PG_W, 8, f'CATALOGO DIGITAL  -  {len(lista)} imagens', border=0, align='C')

pdf.set_font('Arial', '', 10)
pdf.set_text_color(*CINZA3)
pdf.set_xy(0, info_y + 10)
pdf.cell(PG_W, 6, f'{len(cats)} categorias', border=0, align='C')

pdf.set_font('Arial', 'B', 10)
pdf.set_text_color(*BRANCO)
pdf.set_xy(0, info_y + 24)
pdf.cell(PG_W, 6, 'Para fazer seu pedido:', border=0, align='C')
pdf.set_font('Arial', '', 10)
pdf.set_text_color(*CINZA3)
pdf.set_xy(0, info_y + 31)
pdf.cell(PG_W, 6, 'informe o numero da imagem pelo WhatsApp', border=0, align='C')

pdf.set_font('Arial', 'B', 12)
pdf.set_text_color(*CIANO)
pdf.set_xy(0, info_y + 45)
pdf.cell(PG_W, 6, 'WhatsApp ' + WHATSAPP, border=0, align='C')
pdf.set_font('Arial', '', 9)
pdf.set_text_color(*CINZA3)
pdf.set_xy(0, info_y + 53)
pdf.cell(PG_W, 6, EMAIL + '   |   ' + WEBSITE, border=0, align='C')

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
