#!/usr/bin/env bash
# =====================================================================
#  TopFood Embalagens — RECUPERAÇÃO no VPS (Ubuntu 24.04)
#  Reinstala o site do zero a partir do GitHub, replicando o ambiente
#  documentado no DEPLOY.md do projeto: /var/www/topfood + pm2 + nginx.
#
#  USO (no servidor, como root):  bash deploy_topfood.sh
# =====================================================================
set -euo pipefail

DOMINIO="topfoodembalagens.com.br"
APP_DIR="/var/www/topfood"
REPO_HTTPS="https://github.com/wellingtonrisieri09-a11y/topfood"
REPO_SSH="git@github.com:wellingtonrisieri09-a11y/topfood.git"
EMAIL="${TOPFOOD_EMAIL:-wellingtonrisieri09@gmail.com}"

echo "=============================================="
echo " TopFood — recuperação"
echo "   Domínio: $DOMINIO"
echo "   Pasta:   $APP_DIR"
echo "=============================================="

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y nginx git build-essential python3 ca-certificates curl

# --- Node.js 20 LTS (NodeSource) -------------------------------------
if ! command -v node >/dev/null 2>&1 || [ "$(node -v | cut -c2-3)" -lt 18 ]; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y nodejs
fi
echo ">> Node $(node -v) / npm $(npm -v)"
command -v pm2 >/dev/null 2>&1 || npm install -g pm2 >/dev/null

# --- Código -----------------------------------------------------------
mkdir -p /var/www
if [ ! -d "$APP_DIR/.git" ]; then
  echo ">> Clonando o repositório (precisa estar público neste momento)..."
  git clone "$REPO_HTTPS" "$APP_DIR"
else
  echo ">> Repositório já existe — atualizando..."
  git -C "$APP_DIR" pull --ff-only || true
fi
cd "$APP_DIR"

# --- Dependências ------------------------------------------------------
echo ">> npm install (pode demorar alguns minutos: compila o SQLite)..."
# --legacy-peer-deps: o baileys (WhatsApp) declara sharp antigo como peer
# opcional e conflita com o sharp 0.35 do projeto — era assim no VPS antigo.
npm install --legacy-peer-deps

# --- Configuração (.env) ----------------------------------------------
if [ ! -f .env ] && [ -f .env.example ]; then
  cp .env.example .env
  echo ">> .env criado a partir do .env.example (chaves de PIX/NF-e/WhatsApp"
  echo "   precisam ser preenchidas depois — o site sobe mesmo assim)."
fi

# --- Banco de dados -----------------------------------------------------
mkdir -p data
if [ ! -f data/topfood.db ] && [ -f migrate_sqlite.js ]; then
  echo ">> Criando banco a partir dos JSONs (migrate_sqlite.js)..."
  node migrate_sqlite.js || echo "AVISO: migração falhou — o server pode criar o banco sozinho."
fi

# --- Porta do app (padrão 3000, ou PORT= do .env) -----------------------
PORTA="$(grep -E '^PORT=' .env 2>/dev/null | cut -d= -f2 || true)"
PORTA="${PORTA:-3000}"

# --- pm2: processo 'topfood' -------------------------------------------
pm2 describe topfood >/dev/null 2>&1 && pm2 restart topfood || pm2 start server.js --name topfood
pm2 save
CMD_STARTUP="$(pm2 startup systemd -u root --hp /root 2>/dev/null | grep -E 'systemctl|env PATH' | tail -1 || true)"
[ -n "$CMD_STARTUP" ] && eval "$CMD_STARTUP" || true
pm2 save >/dev/null 2>&1 || true

# --- nginx --------------------------------------------------------------
cat > /etc/nginx/sites-available/topfood <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name $DOMINIO www.$DOMINIO;
    client_max_body_size 100M;
    location / {
        proxy_pass         http://127.0.0.1:$PORTA;
        proxy_http_version 1.1;
        proxy_set_header   Host              \$host;
        proxy_set_header   X-Real-IP         \$remote_addr;
        proxy_set_header   X-Forwarded-For   \$proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto \$scheme;
        proxy_set_header   Upgrade           \$http_upgrade;
        proxy_set_header   Connection        "upgrade";
        proxy_read_timeout 300;
    }
}
EOF
ln -sf /etc/nginx/sites-available/topfood /etc/nginx/sites-enabled/topfood
nginx -t
systemctl enable --now nginx
systemctl reload nginx

# --- Teste local ---------------------------------------------------------
sleep 2
echo ">> Teste do app: HTTP $(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORTA" || echo FALHOU)"

# --- HTTPS ---------------------------------------------------------------
apt-get install -y certbot python3-certbot-nginx
if certbot --nginx -d "$DOMINIO" -d "www.$DOMINIO" \
      --non-interactive --agree-tos -m "$EMAIL" --redirect; then
  SSL_OK="sim"
else
  SSL_OK="nao"
fi

# --- Auto-deploy (cron do DEPLOY.md) --------------------------------------
if [ -f "$APP_DIR/deploy.sh" ]; then
  chmod +x "$APP_DIR/deploy.sh"
  ( crontab -l 2>/dev/null | grep -v 'topfood/deploy.sh'; \
    echo '*/2 * * * * /var/www/topfood/deploy.sh >> /var/log/topfood-deploy.log 2>&1' ) | crontab -
fi

# --- Chave SSH p/ GitHub (permite voltar o repo a privado) ----------------
if [ ! -f /root/.ssh/id_ed25519 ]; then
  mkdir -p /root/.ssh && chmod 700 /root/.ssh
  ssh-keygen -t ed25519 -N "" -f /root/.ssh/id_ed25519 -C "topfood-vps" -q
fi
ssh-keyscan -t ed25519 github.com >> /root/.ssh/known_hosts 2>/dev/null || true
git -C "$APP_DIR" remote set-url origin "$REPO_SSH"

echo ""
echo "=============================================="
echo " TOPFOOD RECUPERADO"
echo "----------------------------------------------"
echo " Site:   http://$DOMINIO"
[ "$SSL_OK" = "sim" ] && echo " HTTPS:  ATIVO -> https://$DOMINIO"
echo " Admin:  https://$DOMINIO/admin.html (user: wellington)"
echo ""
echo " >>> PASSO FINAL (para voltar o repo a PRIVADO sem quebrar"
echo " >>> o auto-deploy): adicione esta chave em GitHub ->"
echo " >>> topfood -> Settings -> Deploy keys -> Add deploy key:"
echo ""
cat /root/.ssh/id_ed25519.pub
echo ""
echo " Depois de adicionar a chave, pode voltar o repositório"
echo " para privado que o auto-deploy continua funcionando."
echo "=============================================="
pm2 status topfood || true
