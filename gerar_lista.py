import os
import json
from pathlib import Path

PASTA_RAIZ = os.environ.get('ARTECROMO_BANCO', r"E:\Banco de Imagens")

EXTENSOES = {".jpg", ".jpeg", ".png", ".gif", ".tiff", ".tif", ".webp", ".bmp"}

SKIP_DIRS = {
    "PSD", "CDR", "PDF", "_THUMBS", "_DUPLICATAS", "_EXCLUIDOS",
    "ARQUIVOS DE TRABALHO", "__PYCACHE__", "_WEB"
}

def descobrir_categorias(raiz):
    cats = []
    raiz_path = Path(raiz)
    for item in sorted(raiz_path.iterdir()):
        if not item.is_dir():
            continue
        nome = item.name
        if nome.upper() in SKIP_DIRS or nome.startswith('__'):
            continue
        if nome == "_Excluidos":
            continue
        tem_sub = any(
            sub.is_dir() and sub.name.upper() not in SKIP_DIRS
            and sub.name.upper() not in {"JPG","PNG","GIF","TIFF","OUTROS","BMP","WEBP"}
            for sub in item.iterdir()
            if sub.is_dir()
        )
        if tem_sub:
            for sub in sorted(item.iterdir()):
                if sub.is_dir() and sub.name.upper() not in SKIP_DIRS \
                   and sub.name.upper() not in {"JPG","PNG","GIF","TIFF","OUTROS","BMP","WEBP"}:
                    cats.append(f"{nome}/{sub.name}")
        else:
            cats.append(nome)
    cats = sorted(cats, key=lambda c: (0 if c == "Lançamentos" else 1, c))
    cats.append("_Excluidos")
    return cats

# ── Carregar JSON existente (preservar ordem) ─────────
saida = os.path.join(PASTA_RAIZ, "lista_imagens.json")
existentes = []
existentes_por_img = {}  # img_rel -> produto existente
try:
    with open(saida, encoding="utf-8") as f:
        existentes = json.load(f)
    existentes_por_img = {p["img"]: p for p in existentes}
    print(f"JSON existente: {len(existentes)} entradas (ordem preservada)")
except Exception:
    print("JSON nao encontrado — criando do zero")

# ── Descobrir todos os arquivos no disco ──────────────
CATEGORIAS = descobrir_categorias(PASTA_RAIZ)
print(f"Categorias encontradas: {len(CATEGORIAS)}")

arquivos_disco = {}  # img_rel -> {nome, cat, img, thumb}

for categoria in CATEGORIAS:
    pasta_cat = os.path.join(PASTA_RAIZ, categoria.replace("/", os.sep))
    if not os.path.exists(pasta_cat):
        continue
    for dirpath, dirs, filenames in os.walk(pasta_cat):
        pasta_nome = os.path.basename(dirpath).upper()
        if pasta_nome in SKIP_DIRS:
            dirs[:] = []
            continue
        dirs[:] = [d for d in dirs if d.upper() not in SKIP_DIRS]

        for filename in sorted(filenames):
            ext = Path(filename).suffix.lower()
            if ext not in EXTENSOES:
                continue
            caminho_completo = os.path.join(dirpath, filename)
            caminho_relativo = os.path.relpath(caminho_completo, PASTA_RAIZ).replace("\\", "/")

            thumb_dir = os.path.join(dirpath, "_thumbs")
            thumb_file = os.path.join(thumb_dir, Path(filename).stem + ".jpg")
            if os.path.exists(thumb_file):
                thumb_rel = os.path.relpath(thumb_file, PASTA_RAIZ).replace("\\", "/")
            else:
                thumb_rel = caminho_relativo

            cat_label = categoria.replace("/", " › ")
            arquivos_disco[caminho_relativo] = {
                "nome":  Path(filename).stem,
                "cat":   cat_label,
                "img":   caminho_relativo,
                "thumb": thumb_rel,
            }

# ── Calcular próximo ID disponível ───────────────────
max_id = max((p["id"] for p in existentes), default=0)

# ── Montar lista final preservando ordem ─────────────
# 1. Manter itens existentes que ainda existem no disco (preserva ordem e cat)
produtos = []
for p in existentes:
    if p["img"] in arquivos_disco:
        # Atualiza thumb (pode ter sido gerada agora) mas preserva cat e ordem
        disco = arquivos_disco[p["img"]]
        p_atualizado = dict(p)
        p_atualizado["thumb"] = disco["thumb"]
        # Se a imagem foi movida de pasta (cat mudou), atualiza cat
        # MAS só se a diferença for real (não sobrescreve mudanças manuais)
        produtos.append(p_atualizado)

# 2. Adicionar arquivos novos que não estavam no JSON (vai para o final)
imgs_existentes = {p["img"] for p in produtos}
novos = []
for img_rel, info in arquivos_disco.items():
    if img_rel not in imgs_existentes:
        max_id += 1
        novos.append({
            "id":    max_id,
            "nome":  info["nome"],
            "cat":   info["cat"],
            "img":   info["img"],
            "thumb": info["thumb"],
        })

if novos:
    print(f"Novos arquivos adicionados: {len(novos)}")
    produtos = novos + produtos  # novos vão para Lançamentos (início)

removidos = len(existentes) - (len(produtos) - len(novos))
if removidos > 0:
    print(f"Arquivos removidos do disco: {removidos}")

print(f"Total final: {len(produtos)} imagens")

# ── Salvar ────────────────────────────────────────────
with open(saida, "w", encoding="utf-8") as f:
    json.dump(produtos, f, ensure_ascii=False, indent=2)
print(f"Salvo em: {saida}")

from collections import Counter
cats = Counter(p['cat'] for p in produtos)
for cat, qtd in sorted(cats.items()):
    print(f"  {cat:<30} {qtd:>5}")
