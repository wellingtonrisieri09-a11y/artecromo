# -*- coding: utf-8 -*-
"""
Atualiza o array PRODUTOS no correcao_manual.html
com os dados reais do lista_imagens.json,
preservando todo o resto do HTML (CSS, JS, novas funcionalidades).
"""
import json, re, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

import os as _os; BANCO = Path(_os.environ.get('ARTECROMO_BANCO', r"E:\Banco de Imagens"))

# 1. Ler JSON atualizado
with open(BANCO / "lista_imagens.json", encoding='utf-8') as f:
    produtos = json.load(f)

print(f"Produtos no JSON: {len(produtos)}")

# 2. Ler HTML atual
html_path = BANCO / "correcao_manual.html"
with open(html_path, encoding='utf-8') as f:
    html = f.read()

# 3. Encontrar e substituir apenas o array PRODUTOS
# O array começa com "var PRODUTOS = [" e termina com "];"
# seguido de "var TODAS_CATS"
padrao = r'var PRODUTOS = \[.*?\];(\s*var TODAS_CATS)'
novo_json = json.dumps(produtos, ensure_ascii=False, indent=2)

# Usar função lambda para evitar interpretação de $1 como grupo
def substituir(m):
    return f'var PRODUTOS = {novo_json};\n{m.group(1)}'

novo_html = re.sub(padrao, substituir, html, flags=re.DOTALL)

if novo_html == html:
    print("AVISO: Padrao nao encontrado! Tentando padrao alternativo...")
    # Tentar padrao sem espaco
    padrao2 = r'var PRODUTOS=\[.*?\];(\s*var TODAS_CATS)'
    novo_html = re.sub(padrao2, f'var PRODUTOS = {novo_json};\n$1', html, flags=re.DOTALL)
    if novo_html == html:
        print("ERRO: Nao foi possivel encontrar o array PRODUTOS no HTML.")
        sys.exit(1)

# 4. Salvar
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(novo_html)

tamanho = html_path.stat().st_size // 1024
print(f"OK! HTML atualizado — {tamanho} KB")
print(f"Produtos agora: {len(produtos)}")
