#!/usr/bin/env bash
# ============================================================
# Auto-deploy do Arte Cromo — roda na VPS, chamado pelo cron.
# Checa se há push novo na main; se houver, atualiza e reinicia
# SÓ o serviço "artecromo". Nenhum outro site é tocado.
# ============================================================
set -e
cd /var/www/artecromo

BEFORE=$(git rev-parse HEAD)
git fetch origin main --quiet
AFTER=$(git rev-parse origin/main)

# Nada novo? sai sem fazer nada (não reinicia o site à toa)
[ "$BEFORE" = "$AFTER" ] && exit 0

echo "$(date '+%F %T') >> deploy $BEFORE -> $AFTER"
git reset --hard origin/main   # o banco de imagens fica fora do git, intacto

sudo systemctl restart artecromo
echo "$(date '+%F %T') >> ok, no ar"
