cd /var/www/topfood
pm2 stop topfood >/dev/null
ls -la data/
mv data/topfood.db "data/topfood.db.schema-antigo.$(date +%s)" 2>/dev/null
rm -f data/topfood.db-wal data/topfood.db-shm
pm2 restart topfood >/dev/null
sleep 3
echo "--- api/products depois do fix ---"
curl -s http://127.0.0.1:3000/api/products | head -c 300; echo
echo "--- api/settings ---"
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:3000/api/settings
pm2 logs topfood --nostream --lines 15 2>/dev/null | tail -15
