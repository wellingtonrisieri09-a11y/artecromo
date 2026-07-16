#!/usr/bin/env bash
# ============================================================
# Auto-deploy do Nanai Bolos e Doces — roda na VPS, via cron.
# Checa se há push novo no GitHub; se houver, atualiza a pasta.
# Site 100% estático: o nginx serve os arquivos novos na hora,
# NADA é reiniciado — nenhum outro site é tocado.
# ============================================================
set -e
cd /var/www/nanaibolos

# --- HTTPS (roda UMA vez): emite o certificado do endereço provisório ---
# O link https://srv1716345.hstgr.cloud dava "acesso negado" (WhatsApp abre
# links em https). Tenta emitir via certbot uma única vez; resultado no log.
STAMP=/var/www/.nanai-certbot-tentado
if [ ! -d /etc/letsencrypt/live/srv1716345.hstgr.cloud ] && [ ! -f "$STAMP" ]; then
  touch "$STAMP"
  echo "$(date '+%F %T') >> tentando emitir HTTPS para srv1716345.hstgr.cloud"
  certbot --nginx -d srv1716345.hstgr.cloud --redirect \
    -m wellingtonrisieri09@gmail.com --agree-tos -n \
    > /var/log/nanaibolos-certbot.log 2>&1 \
    && echo "$(date '+%F %T') >> HTTPS emitido com sucesso" \
    || echo "$(date '+%F %T') >> certbot falhou (ver /var/log/nanaibolos-certbot.log)"
fi

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
