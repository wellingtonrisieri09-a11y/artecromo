echo "--- wayback: snapshot disponivel? ---"
curl -s "http://archive.org/wayback/available?url=topfoodembalagens.com.br" ; echo
curl -s "http://archive.org/wayback/available?url=topfoodembalagens.com.br/api/products" ; echo
echo "--- lista de snapshots (cdx) ---"
curl -s "http://web.archive.org/cdx/search/cdx?url=topfoodembalagens.com.br*&output=text&fl=timestamp,original,statuscode&filter=statuscode:200&limit=40" | head -40
