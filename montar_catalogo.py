# -*- coding: utf-8 -*-
import json, pathlib, sys
sys.stdout.reconfigure(encoding='utf-8')

import os as _os; pasta = pathlib.Path(_os.environ.get('ARTECROMO_BANCO', r"E:\Banco de Imagens"))
json_path = pasta / "lista_imagens.json"
tmpl_path = pasta / "template_catalogo.html"
html_out  = pasta / "catalogo_arte_cromo.html"

# Ler JSON
with open(json_path, encoding='utf-8') as f:
    lista_json = f.read().strip()

dados = json.loads(lista_json)
print(f"Produtos carregados: {len(dados)}")

# Ler template
with open(tmpl_path, encoding='utf-8') as f:
    template = f.read()

# Verificar placeholder
if "__LISTA_PRODUTOS__" not in template:
    print("ERRO: placeholder __LISTA_PRODUTOS__ nao encontrado no template!")
    sys.exit(1)

# Substituir
html_final = template.replace("__LISTA_PRODUTOS__", lista_json)

# Salvar
with open(html_out, 'w', encoding='utf-8') as f:
    f.write(html_final)

size_kb = html_out.stat().st_size / 1024
print(f"HTML gerado: {html_out}")
print(f"Tamanho   : {size_kb:.0f} KB ({size_kb/1024:.2f} MB)")
print(f"Produtos  : {len(dados)}")
print("OK!")
