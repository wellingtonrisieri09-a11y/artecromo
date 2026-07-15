git -C /opt/artecromo pull --ff-only
systemctl restart artecromo 2>/dev/null
sleep 2
echo "--- site local ---"
curl -s -o /dev/null -w "catalogo: HTTP %{http_code}\n" http://127.0.0.1:8765/catalogo_arte_cromo.html
curl -s http://127.0.0.1:8765/catalogo_arte_cromo.html | grep -c gerarCartaoPedido
systemctl is-active artecromo nginx
