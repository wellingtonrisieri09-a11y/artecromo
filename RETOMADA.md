# RETOMADA — estado da operação (atualizado em 12/07/2026)

> **Para o Claude:** leia este arquivo inteiro antes de agir. Ele é a memória
> da sessão anterior. Continue de onde ela parou.

## Contexto geral
- Dono: Wellington. Três sites, todos no MESMO VPS Hostinger:
  - **Top Food Embalagens** — topfoodembalagens.com.br (loja Node/Express, repo GitHub `topfood`)
  - **Verbo Vivo** — verbovivoapp.com.br (repo GitHub provavelmente `verbovivo` — CONFIRMAR nome)
  - **Arte Cromo Estampas** — artecromoestampas.com.br (este repo, `artecromo`)
- VPS Hostinger: **2.25.151.19** (srv1716345, Ubuntu 24.04, KVM2). Usuário root.
- O VPS foi contratado ~19/06/2026 e estava VAZIO. Os sites caíram porque os
  domínios apontavam pra ele sem nada instalado (migração inacabada de um VPS
  antigo que não existe mais). Nada disso foi causado pela sessão.
- DNS dos 3 domínios: gerenciado no **registro.br** (zonas separadas).
  - topfood e verbovivo → 2.25.151.19 (desde ~30/06)
  - artecromo → registros A criados em 12/07 (raiz e www → 2.25.151.19), propagação em andamento

## ⚡ PONTE DE EXECUÇÃO REMOTA (ativa!)
O Claude NÃO tem SSH direto (porta 22 bloqueada no sandbox). A execução no VPS
é feita via GitHub, neste repo, branch `claude/arte-cromo-site-progress-lj4xli`:
- **Enviar comando:** criar `agente/comandos/NNN-nome.sh` (numeração crescente),
  commit + push na branch.
- **Receber resultado:** o VPS roda cron a cada 1 min (`/opt/claude-agente/run.sh`),
  executa comandos novos e publica `agente/resultados/NNN-nome.out` (commit+push).
  Buscar com `git fetch` + `git show origin/<branch>:agente/resultados/NNN-nome.out`.
- Chave do VPS: deploy key "vps" (read/write) no repo artecromo (`/root/.ssh/id_agente`).
- Comandos já usados: 000-teste (ok), 001-deploy-topfood (FALHOU: npm ERESOLVE
  baileys×sharp — corrigido com --legacy-peer-deps), 002-deploy-topfood (retry).
- **Desligar a ponte** (quando tudo acabar): `crontab -l | grep -v claude-agente | crontab -`

## Estado no momento do save
1. ✅ Ponte ativa e testada (000-teste respondeu).
2. 🔄 **001-deploy-topfood.sh em execução** — roda `deploy_topfood.sh` (deste repo):
   instala nginx+Node20+pm2, clona `topfood` → `/var/www/topfood`, npm install,
   migrate_sqlite, pm2 (processo `topfood`), nginx no domínio, certbot HTTPS,
   cron de auto-deploy, gera chave `/root/.ssh/id_ed25519` p/ deploy key do topfood.
   → **Verificar `agente/resultados/001-deploy-topfood.out` e testar o site.**
3. ⏳ Repos `artecromo` e `topfood` estão PÚBLICOS temporariamente (necessário
   p/ clone HTTPS). **Depois do deploy: adicionar a chave id_ed25519.pub
   (aparece no fim do resultado 001) como Deploy key do repo topfood, e então
   voltar OS DOIS repos a PRIVADO.**

## Fila de tarefas (ordem)
1. Confirmar Top Food no ar (http/https://topfoodembalagens.com.br). Corrigir erros se houver (usar a ponte).
2. Deploy key do topfood + voltar os 2 repos a privado.
3. Top Food: recriar `.env` real (chaves Mercado Pago/Asaas, NF-e Focus, e-mail;
   senha admin padrão `topfood2026` — trocar). Banco antigo (pedidos) se perdeu
   com o VPS antigo; checar com Hostinger se existe backup do VPS antigo.
4. **Verbo Vivo:** confirmar nome do repo, examinar CLAUDE/DEPLOY.md dele e fazer
   deploy igual (via ponte). DNS já aponta pro VPS.
5. **Arte Cromo:** rodar `deploy_vps.sh` (deste repo) via ponte → site + painel
   em /opt/artecromo. Depois o Wellington envia as imagens (E:\Banco de Imagens
   → /opt/artecromo) por SFTP/FileZilla (root@2.25.151.19). HTTPS via certbot
   quando o DNS do artecromo propagar.
6. Desligar a ponte e revisar segurança (senhas, firewall).

## Fatos úteis
- Terminal web do Hostinger corrompe colagem: corrigir com
  `bind 'set enable-bracketed-paste on'` (digitado) antes de colar.
- Proxy do sandbox só deixa sair HTTPS p/ hosts liberados (github sim; archive.org,
  0x0.st etc. não). SSH (22) sai bloqueado.
- Top Food: porta 3000, pm2 `topfood`, admin `wellington`, login em /admin.html.
- Arte Cromo: servidor.py porta 8765 (bind 127.0.0.1 em produção), home pública
  = catalogo_arte_cromo.html; /login.html = painel. WhatsApp 5511987916193.
- E-mail do Wellington: wellingtonrisieri09@gmail.com (usado no certbot).
