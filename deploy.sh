#!/usr/bin/env bash
# ============================================================
# Auto-deploy do Nanai Bolos e Doces — roda na VPS, via cron.
# Checa se há push novo no GitHub; se houver, atualiza a pasta.
# Site 100% estático: o nginx serve os arquivos novos na hora,
# NADA é reiniciado — nenhum outro site é tocado.
# ============================================================
set -e
cd /var/www/nanaibolos

# Branch publicada (quando o site for para a main, troque aqui)
BRANCH=claude/nanai-bolus-website-f5pwte

BEFORE=$(git rev-parse HEAD)
git fetch origin "$BRANCH" --quiet
AFTER=$(git rev-parse "origin/$BRANCH")

# Nada novo? sai sem fazer nada
[ "$BEFORE" = "$AFTER" ] && exit 0

echo "$(date '+%F %T') >> deploy $BEFORE -> $AFTER"
git reset --hard "origin/$BRANCH"
echo "$(date '+%F %T') >> ok, no ar"
