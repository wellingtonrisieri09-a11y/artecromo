export PATH="$PATH:/usr/local/bin"
pm2 ping >/dev/null 2>&1
pm2 resurrect >/dev/null 2>&1
pm2 describe topfood >/dev/null 2>&1 || (cd /var/www/topfood && pm2 start server.js --name topfood)
pm2 save >/dev/null 2>&1
CMD=$(pm2 startup systemd -u root --hp /root 2>/dev/null | grep -E 'systemctl|env PATH' | tail -1)
[ -n "$CMD" ] && eval "$CMD" >/dev/null 2>&1
pm2 save >/dev/null 2>&1
systemctl start nginx 2>/dev/null
sleep 2
echo "topfood: $(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3000)"
echo "nginx: $(systemctl is-active nginx)"
pm2 ls | grep topfood
