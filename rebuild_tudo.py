# -*- coding: utf-8 -*-
"""
rebuild_tudo.py — "cerebro" da Arte Cromo.

Sempre que o catalogo muda (enviar, mover, reordenar, excluir, renomear),
este script deixa TUDO em sincronia:

  1. ORGANIZA a lista: agrupa por categoria (Lancamentos sempre no topo),
     preservando a ordem manual dentro de cada categoria.
     -> a numeracao fica SEMPRE em sequencia (numero = posicao na lista)
        e igual no site e no PDF.

  2. REGENERA tudo junto:
       - site        (montar_catalogo.py)
       - painel admin (atualizar_produtos_html.py)
       - catalogo PDF (gerar_pdf.py)
"""
import os, sys, json, subprocess, datetime
from pathlib import Path
from collections import OrderedDict

BANCO = Path(os.environ.get('ARTECROMO_BANCO', '/var/www/artecromo'))
JSON  = BANCO / 'lista_imagens.json'


def log(msg):
    print(msg, flush=True)


def organizar():
    """Agrupa por categoria (Lancamentos primeiro), mantendo a ordem interna.
       Renumera implicitamente: o numero de cada imagem = sua posicao na lista."""
    with open(JSON, encoding='utf-8') as f:
        lista = json.load(f)

    por_cat = OrderedDict()
    for p in lista:
        por_cat.setdefault(p.get('cat', 'Outros'), []).append(p)
    cats = list(por_cat.keys())

    # Lancamentos sempre no topo; o resto na ordem de primeira aparicao.
    ordem = [c for c in cats if c == 'Lançamentos'] + [c for c in cats if c != 'Lançamentos']
    nova = []
    for c in ordem:
        nova.extend(por_cat[c])

    if nova != lista:
        with open(JSON, 'w', encoding='utf-8') as f:
            json.dump(nova, f, ensure_ascii=False, indent=2)
        try:
            os.chmod(str(JSON), 0o644)
        except Exception:
            pass
        log(f'Lista organizada: {len(nova)} imagens em {len(cats)} categorias (Lancamentos no topo).')
    else:
        log(f'Lista ja estava organizada: {len(nova)} imagens em {len(cats)} categorias.')
    return len(nova)


def rodar(script):
    py = sys.executable
    env = dict(os.environ, ARTECROMO_BANCO=str(BANCO))
    log(f'-> {script}')
    r = subprocess.run([py, str(BANCO / script)], env=env, cwd=str(BANCO),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    saida = (r.stdout or '').strip().splitlines()
    if saida:
        log('   ' + saida[-1])
    if r.returncode != 0:
        log(f'   ERRO em {script} (codigo {r.returncode})')
    return r.returncode == 0


def main():
    log('=== REBUILD ' + datetime.datetime.now().strftime('%d/%m %H:%M:%S') + ' ===')
    total = organizar()
    ok1 = rodar('montar_catalogo.py')         # site
    ok2 = rodar('atualizar_produtos_html.py') # painel admin
    ok3 = rodar('gerar_pdf.py')               # catalogo PDF
    if ok1 and ok2 and ok3:
        log(f'REBUILD COMPLETO — {total} imagens. Site + painel + PDF em sincronia.')
    else:
        log('REBUILD terminou COM ERROS (veja acima).')


if __name__ == '__main__':
    main()
