cat > /opt/claude-agente/run.sh.novo <<'RUN'
#!/usr/bin/env bash
exec 9>/var/lock/claude-agente.lock
flock -n 9 || exit 0
export GIT_SSH_COMMAND="ssh -i /root/.ssh/id_agente -o StrictHostKeyChecking=accept-new"
export GIT_TERMINAL_PROMPT=0
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
  timeout -k 30 1500 bash "$f" >> "$out" 2>&1 </dev/null
  rc=$?
  [ $rc -eq 124 ] && echo "!! ESTOURO DE TEMPO (25 min) — comando interrompido" >> "$out"
  echo "== fim (exit $rc) ==" >> "$out"
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
chmod +x /opt/claude-agente/run.sh.novo
mv /opt/claude-agente/run.sh.novo /opt/claude-agente/run.sh
echo "ponte blindada: timeout de 25min por comando"
