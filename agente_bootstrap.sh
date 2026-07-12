#!/usr/bin/env bash
# =====================================================================
#  Ponte Claude <-> VPS via GitHub (cole UMA vez no terminal do VPS)
#  - Gera uma chave SSH e espera você cadastrá-la como Deploy key
#    (com escrita) no repositório artecromo.
#  - Instala um executor: a cada 1 min, baixa comandos novos de
#    agente/comandos/*.sh, executa e publica a saída em
#    agente/resultados/ (commit+push).
#  Para DESLIGAR a ponte depois:
#    crontab -l | grep -v claude-agente | crontab -
# =====================================================================
set -u
BRANCH="claude/arte-cromo-site-progress-lj4xli"
REPO_SSH="git@github.com:wellingtonrisieri09-a11y/artecromo.git"
DIR="/opt/claude-agente"
KEY="/root/.ssh/id_agente"

export DEBIAN_FRONTEND=noninteractive
command -v git >/dev/null 2>&1 || { apt-get update -y >/dev/null; apt-get install -y git >/dev/null; }

mkdir -p /root/.ssh && chmod 700 /root/.ssh
[ -f "$KEY" ] || ssh-keygen -t ed25519 -N "" -f "$KEY" -C "claude-agente-vps" -q
ssh-keyscan -t ed25519 github.com >> /root/.ssh/known_hosts 2>/dev/null || true

echo ""
echo "=================================================================="
echo " COPIE A CHAVE ABAIXO e cadastre no GitHub:"
echo "   artecromo -> Settings -> Deploy keys -> Add deploy key"
echo "   Title: vps   |   MARQUE a caixa 'Allow write access'!"
echo "=================================================================="
cat "$KEY.pub"
echo "=================================================================="
echo " Aguardando a chave ser cadastrada (verifico a cada 10s)..."

export GIT_SSH_COMMAND="ssh -i $KEY -o StrictHostKeyChecking=accept-new"
OK=""
for i in $(seq 1 90); do
  if git ls-remote "$REPO_SSH" HEAD >/dev/null 2>&1; then OK=1; break; fi
  sleep 10
done
if [ -z "$OK" ]; then
  echo "ERRO: a chave nao foi autorizada em 15 minutos. Cadastre-a e rode este script de novo."
  exit 1
fi
echo ">> Chave aceita pelo GitHub! Instalando o executor..."

mkdir -p "$DIR"
rm -rf "$DIR/repo"
git clone -q -b "$BRANCH" "$REPO_SSH" "$DIR/repo"
git -C "$DIR/repo" config user.name  "VPS Agente"
git -C "$DIR/repo" config user.email "vps-agente@localhost"

cat > "$DIR/run.sh" <<'RUN'
#!/usr/bin/env bash
# Executor da ponte: roda comandos novos e publica os resultados.
exec 9>/var/lock/claude-agente.lock
flock -n 9 || exit 0
export GIT_SSH_COMMAND="ssh -i /root/.ssh/id_agente -o StrictHostKeyChecking=accept-new"
B="claude/arte-cromo-site-progress-lj4xli"
D="/opt/claude-agente/repo"
cd "$D" || exit 1
git fetch -q origin "$B" || exit 1
git reset -q --hard "origin/$B"
mkdir -p agente/comandos agente/resultados
NOVO=0
for f in agente/comandos/*.sh; do
  [ -e "$f" ] || continue
  b="$(basename "$f" .sh)"
  out="agente/resultados/$b.out"
  [ -e "$out" ] && continue
  echo "== executando $b em $(date '+%F %T') ==" > "$out"
  bash "$f" >> "$out" 2>&1
  echo "== fim (exit $?) ==" >> "$out"
  NOVO=1
done
if [ "$NOVO" = 1 ]; then
  git add agente/resultados
  git commit -q -m "agente: resultados $(date '+%F %T')"
  n=0
  until git push -q origin "HEAD:$B"; do
    n=$((n+1)); [ "$n" -ge 3 ] && break
    git pull --rebase -q origin "$B" || true
    sleep 2
  done
fi
RUN
chmod +x "$DIR/run.sh"

( crontab -l 2>/dev/null | grep -v 'claude-agente' ; \
  echo '* * * * * /opt/claude-agente/run.sh >/dev/null 2>&1' ) | crontab -

"$DIR/run.sh" || true

echo ""
echo "=================================================================="
echo " PONTE ATIVA! O Claude ja consegue executar comandos neste VPS."
echo " (agora voce ja pode voltar o repositorio artecromo a PRIVADO —"
echo "  a ponte continua funcionando pela chave SSH)"
echo "=================================================================="
