echo "--- home ---"; curl -sk -o /dev/null -w "HTTP %{http_code} em %{time_total}s\n" https://topfoodembalagens.com.br
echo "--- api products ---"; curl -sk https://topfoodembalagens.com.br/api/products | head -c 400; echo
echo "--- titulo da pagina ---"; curl -sk https://topfoodembalagens.com.br | grep -o -m1 "<title>[^<]*"
