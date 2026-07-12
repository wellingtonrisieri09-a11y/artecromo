#!/usr/bin/env bash
# =====================================================================
#  Arte Cromo — instalador do site no VPS (Ubuntu 22/24)
#  Sobe o catálogo + painel (servidor.py) atrás do nginx, com HTTPS.
#
#  USO (no servidor, como root):
#     bash deploy_vps.sh
#
#  Requisitos: a pasta do "Banco de Imagens" (com servidor.py, o
#  catálogo, os scripts e as imagens) já enviada para /opt/artecromo
#  (ou informe outro caminho em ARTECROMO_DIR).
# =====================================================================
set -euo pipefail

DOMINIO="${1:-artecromoestampas.com.br}"
APP_DIR="${ARTECROMO_DIR:-/opt/artecromo}"
PORT="${ARTECROMO_PORT:-8765}"
EMAIL="${ARTECROMO_EMAIL:-wellingtonrisieri09@gmail.com}"

echo "======================================================"
echo " Arte Cromo — deploy"
echo "   Domínio : $DOMINIO"
echo "   Pasta   : $APP_DIR"
echo "   Porta   : $PORT (interna, atrás do nginx)"
echo "======================================================"

# --- 0) Código: baixa do GitHub se ainda não estiver no servidor -----
REPO_URL="${ARTECROMO_REPO:-https://github.com/wellingtonrisieri09-a11y/artecromo}"
REPO_BRANCH="${ARTECROMO_BRANCH:-claude/arte-cromo-site-progress-lj4xli}"
if [ ! -f "$APP_DIR/servidor.py" ]; then
  echo ">> Código não encontrado em $APP_DIR — baixando do GitHub..."
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -y >/dev/null
  apt-get install -y git >/dev/null
  git clone --depth 1 -b "$REPO_BRANCH" "$REPO_URL" "$APP_DIR"
elif [ -d "$APP_DIR/.git" ]; then
  echo ">> Atualizando código a partir do GitHub..."
  git -C "$APP_DIR" pull --ff-only || true
fi
if [ ! -f "$APP_DIR/servidor.py" ]; then
  echo "ERRO: não encontrei $APP_DIR/servidor.py mesmo após o download."
  echo "(o repositório está privado? Torne-o público ou envie os arquivos por SFTP)"
  exit 1
fi

# --- 1) Pacotes do sistema ------------------------------------------
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y nginx python3 python3-venv python3-pip \
                   certbot python3-certbot-nginx

# --- 2) Ambiente Python + dependências ------------------------------
if [ ! -d "$APP_DIR/.venv" ]; then
  python3 -m venv "$APP_DIR/.venv"
fi
"$APP_DIR/.venv/bin/pip" install --upgrade pip >/dev/null
"$APP_DIR/.venv/bin/pip" install pillow fpdf2 requests >/dev/null

# --- 3) Senha do painel admin ---------------------------------------
# Mantém a senha entre execuções (guardada em /etc/artecromo.env).
ENV_FILE="/etc/artecromo.env"
if [ -f "$ENV_FILE" ] && grep -q ARTECROMO_SENHA "$ENV_FILE"; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
else
  ARTECROMO_SENHA="$(python3 -c 'import secrets;print(secrets.token_urlsafe(9))')"
  cat > "$ENV_FILE" <<EOF
ARTECROMO_USUARIO=admin
ARTECROMO_SENHA=$ARTECROMO_SENHA
EOF
  chmod 600 "$ENV_FILE"
fi

# --- 4) Serviço systemd (servidor.py sempre no ar) ------------------
cat > /etc/systemd/system/artecromo.service <<EOF
[Unit]
Description=Arte Cromo — servidor.py (catálogo + painel)
After=network.target

[Service]
WorkingDirectory=$APP_DIR
EnvironmentFile=$ENV_FILE
Environment=ARTECROMO_BANCO=$APP_DIR
Environment=ARTECROMO_PORT=$PORT
Environment=ARTECROMO_HOST=127.0.0.1
Environment=ARTECROMO_DOMINIO=$DOMINIO
Environment=ARTECROMO_ABRIR_NAV=0
ExecStart=$APP_DIR/.venv/bin/python $APP_DIR/servidor.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now artecromo
systemctl restart artecromo

# --- 5) nginx (domínio -> servidor.py; home abre o catálogo) --------
cat > /etc/nginx/sites-available/artecromo <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name $DOMINIO www.$DOMINIO;

    client_max_body_size 200M;

    # Página inicial pública = catálogo (a raiz do painel iria pro login)
    location = / { return 302 /catalogo_arte_cromo.html; }

    location / {
        proxy_pass         http://127.0.0.1:$PORT;
        proxy_http_version 1.1;
        proxy_set_header   Host              \$host;
        proxy_set_header   X-Real-IP         \$remote_addr;
        proxy_set_header   X-Forwarded-For   \$proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300;
    }
}
EOF

ln -sf /etc/nginx/sites-available/artecromo /etc/nginx/sites-enabled/artecromo
nginx -t
systemctl reload nginx

# --- 6) HTTPS (Let's Encrypt) — só se o DNS já apontar pra cá --------
echo ""
echo ">> Tentando emitir o certificado HTTPS..."
if certbot --nginx -d "$DOMINIO" -d "www.$DOMINIO" \
       --non-interactive --agree-tos -m "$EMAIL" --redirect ; then
  SSL_OK="sim"
else
  SSL_OK="nao"
fi

# --- Resumo ----------------------------------------------------------
echo ""
echo "======================================================"
echo " DEPLOY CONCLUÍDO"
echo "------------------------------------------------------"
echo " Site:    http://$DOMINIO   (catálogo)"
echo " Painel:  http://$DOMINIO/login.html"
echo " Login:   admin"
echo " Senha:   $ARTECROMO_SENHA"
echo "          (guardada em $ENV_FILE)"
if [ "$SSL_OK" = "sim" ]; then
  echo " HTTPS:   ATIVO  ->  https://$DOMINIO"
else
  echo " HTTPS:   ainda não (o DNS provavelmente não propagou)."
  echo "          Quando o domínio já apontar pro IP deste VPS, rode:"
  echo "          certbot --nginx -d $DOMINIO -d www.$DOMINIO --redirect -m $EMAIL --agree-tos"
fi
echo "======================================================"
echo " Status do serviço:"
systemctl --no-pager --lines=0 status artecromo | head -5 || true
