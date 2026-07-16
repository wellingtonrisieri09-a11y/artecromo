# 🎂 Nanai Bolos e Doces

Site-cardápio digital da **Nanai Bolos e Doces**, empresa de bolos sob encomenda para
festas e comemorações (aniversário, casamento, Natal, Ano Novo, chá de bebê...).

Estilo cardápio delivery (inspirado no anota.ai): o cliente navega pelos sabores,
monta o pedido no carrinho e **envia direto pelo WhatsApp**.

## 📱 O que o site tem

- **Cardápio completo** com os 20 sabores organizados em 5 categorias
  (Clássicos, Linha Ninho, Mousse de Doce de Leite, Creme Belga, Especiais)
- **Galeria de fotos reais** dos bolos já feitos (26 fotos em `img/fotos/`),
  com visualização ampliada ao tocar
- **Carrinho de pedido**: cliente escolhe sabor, tamanho, quantidade e observações
- **Checkout via WhatsApp**: nome, data da festa, ocasião, retirada/entrega —
  monta a mensagem formatada e abre o WhatsApp
- **Busca de sabores** e navegação por categoria (barra fixa)
- **Logotipo em SVG** (`img/logo.svg`) — versão moderna vetorial do logo original
  (fouet sobre círculo rosa), embutido na capa e usado como favicon
- 100% responsivo, feito para celular. Arquivo único (`index.html`), sem
  dependências — hospeda em qualquer lugar

## ⚙️ Configurar (IMPORTANTE antes de publicar)

Tudo fica no bloco `CONFIG` no início do `<script>` dentro de `index.html`:

1. **Número do WhatsApp** — já configurado com o (11) 95139-7856
   (`5511951397856`). Para trocar, edite `CONFIG.whatsapp`.
2. **Tamanhos e preços** — os valores atuais (R$ 90 / 130 / 170) são
   **provisórios**. Ajuste nomes, pesos e preços na lista `tamanhos`.
3. **Sabores** — para adicionar/editar sabores, mexa na lista `CARDAPIO`
   (logo abaixo do CONFIG). Cada sabor tem nome, descrição e 2 cores da
   ilustração.
4. **Fotos da galeria** — a lista `GALERIA` aponta para os arquivos de
   `img/fotos/`. Para adicionar uma foto nova, coloque o arquivo na pasta e
   acrescente uma linha `{ arq:'nome.jpeg', leg:'Legenda' }`.

## 🚀 Publicar na VPS (mesmo padrão dos outros sites)

Site 100% estático — o nginx serve a pasta direto, **sem processo Node/pm2**.
O repositório já traz a infraestrutura no padrão do servidor
(ver `SERVIDOR.md` do TopFood):

| Item | Valor |
|------|-------|
| Pasta na VPS | `/var/www/nanaibolos` |
| Processo | nenhum (estático) |
| Porta provisória | `8090` (acesso por IP) |
| Link provisório | `http://srv1716345.hstgr.cloud` |
| nginx | `nginx/nanaibolos.conf` |
| Auto-deploy | `deploy.sh` (cron, só puxa o git — não reinicia nada) |

### Montagem (colar UMA vez no terminal da VPS)

```bash
cd /var/www && \
git clone git@github.com:wellingtonrisieri09-a11y/-criador-modelo.git nanaibolos && \
cd nanaibolos && git checkout claude/nanai-bolus-website-f5pwte && \
sudo cp nginx/nanaibolos.conf /etc/nginx/sites-available/nanaibolos && \
sudo ln -sf /etc/nginx/sites-available/nanaibolos /etc/nginx/sites-enabled/nanaibolos && \
sudo nginx -t && sudo systemctl reload nginx && \
( crontab -l 2>/dev/null; echo "4-59/4 * * * * /var/www/nanaibolos/deploy.sh >> /var/log/nanaibolos-deploy.log 2>&1" ) | crontab - && \
echo "✅ Nanai no ar: http://srv1716345.hstgr.cloud"
```

### Quando comprar o domínio

1. Aponte o registro **A** do domínio para o IP da VPS (`2.25.151.19`)
2. O `server_name` já está pronto no conf — só emitir o HTTPS:
   `sudo certbot --nginx -d nanaibolos.com.br -d www.nanaibolos.com.br`

Para testar local: `python3 -m http.server 8000`
