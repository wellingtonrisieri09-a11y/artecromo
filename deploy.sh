#!/usr/bin/env bash
# ============================================================
# Auto-deploy do Nanai Bolos e Doces — roda na VPS, via cron.
# Checa se há push novo no GitHub; se houver, atualiza a pasta.
# Site 100% estático: o nginx serve os arquivos novos na hora,
# NADA é reiniciado — nenhum outro site é tocado.
# ============================================================
set -e
cd /var/www/nanaibolos

# --- HTTPS do endereço provisório (roda UMA vez, com backup e reversão) ---
# O https://srv1716345.hstgr.cloud abria o Arte Cromo: o certificado desse
# hostname já existia no servidor (era usado pelo Arte Cromo antes do domínio
# próprio). Aqui: 1) se não houver certificado, tenta emitir; 2) aponta o
# certificado para o site da Nanai (porta 443) e tira o hostname das configs
# antigas. Se o nginx -t reprovar, restaura tudo do backup.
HOST=srv1716345.hstgr.cloud
LIVE=/etc/letsencrypt/live/$HOST
NGX=/etc/nginx/sites-available/nanaibolos
FALHA=/var/www/.nanai-https-falhou

if [ ! -f "$LIVE/fullchain.pem" ] && [ ! -f /var/www/.nanai-certbot-v2 ]; then
  touch /var/www/.nanai-certbot-v2
  echo "$(date '+%F %T') >> emitindo certificado para $HOST"
  certbot certonly --nginx -d "$HOST" -m wellingtonrisieri09@gmail.com --agree-tos -n \
    > /var/log/nanaibolos-certbot.log 2>&1 || echo "$(date '+%F %T') >> certbot falhou"
fi

if [ -f "$LIVE/fullchain.pem" ] && [ -f "$NGX" ] && ! grep -q "listen 443" "$NGX" && [ ! -f "$FALHA" ]; then
  echo "$(date '+%F %T') >> apontando HTTPS de $HOST para a Nanai"
  BKP=/root/nginx-backup-nanai-$(date +%s)
  mkdir -p "$BKP" && cp -a /etc/nginx/sites-available/. "$BKP/"
  # remove o hostname das configs antigas (Arte Cromo etc.), preservando a sintaxe
  for f in /etc/nginx/sites-available/*; do
    [ "$(basename "$f")" = "nanaibolos" ] && continue
    sed -i -E "s/(server_name[^;]*[ \t])$HOST([ \t;])/\1desativado-hstgr.invalid\2/g; s/(server_name[ \t]+)$HOST;/\1desativado-hstgr.invalid;/g" "$f"
  done
  cat >> "$NGX" <<BLOCO443
server {
    listen 443 ssl;
    server_name $HOST;
    ssl_certificate $LIVE/fullchain.pem;
    ssl_certificate_key $LIVE/privkey.pem;
    root /var/www/nanaibolos;
    index index.html;
    location /img/ { add_header Cache-Control "public, max-age=604800"; }
    location = /index.html { add_header Cache-Control "no-cache"; }
    location / { try_files \$uri \$uri/ /index.html; }
}
BLOCO443
  if nginx -t > /var/log/nanaibolos-https.log 2>&1; then
    systemctl reload nginx
    echo "$(date '+%F %T') >> HTTPS da Nanai no ar em https://$HOST"
  else
    cp -a "$BKP/." /etc/nginx/sites-available/
    touch "$FALHA"
    echo "$(date '+%F %T') >> nginx -t reprovou, configs restauradas do backup $BKP"
  fi
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
