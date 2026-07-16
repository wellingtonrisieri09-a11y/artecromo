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

## 🚀 Publicar

É um site estático — qualquer hospedagem serve (GitHub Pages, Vercel, Netlify,
ou o mesmo servidor dos outros sites com nginx). Basta servir a pasta.

Para testar local:

```bash
npx serve .
# ou
python3 -m http.server 8000
```
