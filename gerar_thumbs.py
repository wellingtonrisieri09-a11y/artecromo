# -*- coding: utf-8 -*-
"""
Gera miniaturas 300x300 para todas as imagens do catálogo.
Salva em _thumbs/ dentro de cada pasta de formato.
"""
import sys, json
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
from PIL import Image
from tqdm import tqdm

import os as _os; BANCO = Path(_os.environ.get('ARTECROMO_BANCO', r"E:\Banco de Imagens"))
JSON_PATH  = BANCO / "lista_imagens.json"
THUMB_SIZE  = (300, 300)
QUALITY     = 72
EXTENSOES   = {'.jpg','.jpeg','.png','.gif','.tiff','.tif','.webp','.bmp'}
MAX_SIZE_MB = 15  # pular arquivos maiores que 15MB (TIFFs pesados)

with open(JSON_PATH, encoding='utf-8') as f:
    produtos = json.load(f)

print(f"Total de imagens: {len(produtos)}")
ok = 0
erros = 0

for p in tqdm(produtos, desc="Thumbs", unit="img"):
    src = BANCO / p['img'].replace('/', '\\')
    if not src.exists():
        erros += 1
        continue

    # Pular arquivos muito grandes (TIFFs de 180MB etc)
    try:
        if src.stat().st_size > MAX_SIZE_MB * 1024 * 1024:
            p['thumb'] = p['img']
            ok += 1
            continue
    except:
        pass

    # Pasta _thumbs dentro da mesma pasta da imagem
    thumb_dir = src.parent / "_thumbs"
    thumb_dir.mkdir(exist_ok=True)
    thumb_path = thumb_dir / (src.stem + ".jpg")

    # Pular se já existe e é recente
    if thumb_path.exists():
        p['thumb'] = str(thumb_path.relative_to(BANCO)).replace('\\', '/')
        ok += 1
        continue

    try:
        img = Image.open(src).convert("RGB")
        # Manter proporção com fundo preto
        img.thumbnail(THUMB_SIZE, Image.LANCZOS)
        # Centralizar em canvas 300x300
        canvas = Image.new("RGB", THUMB_SIZE, (17, 17, 17))
        offset = ((THUMB_SIZE[0] - img.width) // 2,
                  (THUMB_SIZE[1] - img.height) // 2)
        canvas.paste(img, offset)
        canvas.save(thumb_path, "JPEG", quality=QUALITY, optimize=True)
        p['thumb'] = str(thumb_path.relative_to(BANCO)).replace('\\', '/')
        ok += 1
    except Exception as e:
        p['thumb'] = p['img']  # fallback para original
        erros += 1

# Salvar JSON atualizado com campo 'thumb'
with open(JSON_PATH, 'w', encoding='utf-8') as f:
    json.dump(produtos, f, ensure_ascii=False, indent=2)

total_kb = sum((BANCO / p['thumb'].replace('/','\\') ).stat().st_size
               for p in produtos
               if 'thumb' in p and (BANCO / p['thumb'].replace('/','\\') ).exists()) / 1024

print(f"\nThumbs geradas : {ok}")
print(f"Erros          : {erros}")
print(f"Tamanho total  : {total_kb/1024:.1f} MB")
print("JSON atualizado com campo 'thumb'")
