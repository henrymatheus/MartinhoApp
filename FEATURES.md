# Martinho — Funcionalidades

> **Regra do projeto:** este arquivo é a fonte da verdade sobre o que o sistema faz.
> Consulte-o **antes de iniciar qualquer tarefa** e atualize-o **sempre que uma funcionalidade for criada, alterada ou removida**.

Legenda de status: ✅ pronto · 🚧 em andamento · 📋 planejado · 🗄️ legado (desktop Tkinter)

Situação atual: sistema interno (agenda, clientes, histórico, horários, balanço) e agendamento online pelo cliente prontos, instaláveis como app (PWA). No ar em https://martinhoapp.onrender.com (Render + Supabase). 🚧 Hospedagem mudando do Render para a Vercel (plano gratuito), com o mesmo Django e o mesmo banco: falta criar o projeto na Vercel (passo a passo em [backend/README.md](backend/README.md)). Faltam também e-mail de aniversário e backup.

Última atualização: 2026-10-03

---

## 1. Visão geral

Sistema de gestão para barbearias. Nome do app: **Martinho**. Cobre agendamento, cadastro de clientes e histórico de atendimentos.
Está migrando de um app desktop (Python + Tkinter + SQLite) para um app web em Django, com as telas em templates HTML do próprio Django.
A primeira barbearia cliente usará o sistema comercialmente desde o início.

## 2. Arquitetura (custo zero)

| Camada | Tecnologia | Hospedagem |
|---|---|---|
| Sistema (telas + regras) | Django com templates HTML, login por sessão do Django | Vercel (plano Hobby, gratuito). O Django roda como Vercel Function; CSS e imagens saem do CDN da Vercel (`collectstatic` automático no build). Antes: Render |
| Banco | PostgreSQL | Supabase (plano gratuito), pelo pooler em modo transaction (porta 6543), sem conexões persistentes na Vercel |
| Arquivos e fotos | Supabase Storage | O servidor da Vercel não tem disco permanente |
| Tarefas agendadas | GitHub Actions: e-mail de aniversário diário, backup diário com `pg_dump` | GitHub |
| Notificações | Links `wa.me` do WhatsApp (sem API paga) | — |

Regras fixas:
- Segredos ficam sempre em `.env`, nunca no Git.
- Deploy automático a partir do GitHub (projeto da Vercel com Root Directory `backend`). Migrations rodadas à mão: `python manage.py migrate` com a `DATABASE_URL` de produção.
- Um único `python manage.py runserver` abre o sistema em `127.0.0.1:8000`; a administração fica em `/admin/`.
- Desenvolvimento em SQLite; produção no PostgreSQL do Supabase (variável `DATABASE_URL`).
- O CSS vem de `backend/static/css/tokens.css`, gerado a partir de `docs/marca/tokens.json`.

## 3. Identidade visual

- Nome: **Martinho**. Símbolo: um M cortado por uma lâmina dourada.
- Cores: azul-marinho, azul, branco e detalhes em dourado, com tema claro e escuro.
- Fontes: Bodoni Moda (marca e títulos) e Figtree (interface).
- Arquivos e tokens: [docs/marca/](docs/marca/). Guia completo: https://claude.ai/artifact/DBGPR6HYLjxbw6tM4uJdz7
- Componentes definidos no guia: Button, Input, StatusBadge, AppointmentCard e LoadingScreen. No sistema, eles viraram classes CSS em `backend/static/css/martinho.css`.

## 4. Funcionalidades do MVP (web)

| # | Funcionalidade | Status | Observações |
|---|---|---|---|
| 1 | Cadastro de barbearia | ✅ | Pela administração. Base multi-barbearia: cada registro pertence a uma barbearia e cada usuário só vê a sua |
| 2 | Cadastro de barbeiros | ✅ | Pela administração |
| 3 | Cadastro de serviços (nome, preço, duração) | ✅ | Pela administração. Nome único por barbearia |
| 4 | Cadastro de clientes | ✅ | Tela Clientes: lista com busca por nome ou telefone, cadastro, edição e ficha |
| 5 | Agendamento | ✅ | Novo agendamento e remarcação. Conflito de horário verificado no `save()` com trava do barbeiro (`select_for_update`); horários encostados e cancelados não conflitam; fim calculado pela duração do serviço. Ações: Concluir, Faltou, Cancelar |
| 6 | Histórico de atendimentos por cliente | ✅ | Na ficha do cliente. "Concluir atendimento" na agenda registra o histórico com cópia do preço |
| 7 | Agenda do dia (painel) | ✅ | Página inicial. Navegação entre dias, linha dourada "agora", marcador de aniversariante. Dia vazio mostra os próximos 5 horários marcados, com link para o dia |
| 8 | E-mail de aniversário | 📋 | Management command rodado diariamente pelo GitHub Actions |
| 9 | Login | ✅ | Sessão do Django, tela `/entrar/` com a marca |
| 10 | Notificação ao cliente via WhatsApp (`wa.me`) | ✅ | Botão "Lembrar no WhatsApp" com mensagem pronta; telefone com DDD ganha o código 55 |
| 11 | Backup diário do banco | 📋 | `pg_dump` pelo GitHub Actions |
| 12 | Servidor sempre acordado | — | Não é mais necessário: na Vercel o sistema não hiberna como no Render gratuito |
| 13 | Dados de demonstração | ✅ | `python manage.py dados_demo` (só no SQLite), com horários de trabalho e uma folga |
| 14 | Horários de trabalho dos barbeiros | ✅ | Tela Horários: até dois turnos por dia (o intervalo é o almoço) e ausências (folga, férias, consulta), de dias inteiros ou de parte de um dia. Usuário com papel "barbeiro" ligado a um barbeiro só edita os próprios |
| 15 | Agendamento online pelo cliente | ✅ | `/agendar/<endereço-da-barbearia>/`, sem login: barbeiro (cada um com a situação de hoje e o próximo horário livre) → serviço → dias e horários livres daquele barbeiro → nome e WhatsApp. Ausente no dia inteiro: o dia não aparece. Link pessoal de cada barbeiro: `?barbeiro=<id>`. Confirmado na hora. Cliente reconhecido pelo telefone. Máximo de 3 horários futuros por telefone. Horários a cada 15 min, com 1 h de antecedência mínima, até 30 dias à frente |
| 16 | PWA (instalar como app) | ✅ | Manifesto do sistema (`/`) e um por barbearia (página de agendamento), ícones, service worker com página offline |
| 17 | Equipe do dia e faltas | ✅ | Na Agenda: situação de cada barbeiro (atendendo, ausente, sem expediente) e botões "Faltou hoje", "Saiu agora" e "Desfazer ausência". Horários já marcados com quem faltou ficam destacados, com "Avisar cliente no WhatsApp". Nada é cancelado sozinho. O agendamento interno avisa e pede confirmação ("Agendar mesmo assim") |
| 18 | Aviso de novo agendamento ao barbeiro | ✅ | Notificação push (grátis, Web Push/VAPID) quando o cliente agenda pela página. O barbeiro toca em "Ativar avisos" no Martinho. Vai para o barbeiro com login; se ele não tiver, para os donos. Precisa das variáveis `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY` e `VAPID_EMAIL` (`python manage.py gerar_chaves_push`). iPhone: só com o Martinho instalado na tela inicial (iOS 16.4+) |
| 19 | Balanço | ✅ | Tela Balanço: atendimentos do período (hoje, semana, mês, mês passado ou datas escolhidas), gráfico por dia (ou por mês em faixas longas), comparação com o período anterior até o mesmo dia, média por dia, clientes atendidos, faltas, cancelamentos, resumo por barbeiro e lista dia a dia (até 500). Planilha CSV. O barbeiro vê só o próprio. Sem valores em dinheiro por enquanto |
| 20 | Atendimento sem hora marcada | ✅ | "Sem hora marcada" na Agenda / "Registrar atendimento" no Balanço: vai direto para o histórico e o balanço, com cliente da lista ou novo (reconhecido pelo telefone). Data futura recusada; o barbeiro registra só para si |

## 5. Funcionalidades do sistema legado (desktop Tkinter)

Funcionalidades que existiam em `legacy/main.py`, `legacy/agendamento.py` e `legacy/EnvioEmail.py`. A pasta `legacy/` foi removida em 2026-10-03 e fica no histórico do git.

| Funcionalidade | Status | Onde | Situação |
|---|---|---|---|
| Cadastro de cliente (nome, telefone, e-mail, nascimento) | 🗄️ | `main.py` `cadastrar_cliente` | Funciona. Nome salvo em maiúsculas. Validação de telefone e e-mail importada mas não usada |
| Busca de cliente por nome (autocomplete) | 🗄️ | `main.py` `localizar_cliente` | Funciona |
| Edição de cliente (inclui endereço) | 🗄️ | `main.py` `salvar_alteracao_cliente` | Funciona. Identifica o cliente pelo nome, não pelo id |
| Histórico do cliente (data, item, valor) | 🗄️ | `main.py` `preencher_tela_clientes` | Funciona |
| Exportar histórico para Excel | 🗄️ | `main.py` `extrair_historico_cliente` | Funciona. `pandas` não é importado explicitamente, só chega via `agendamento` |
| Registro de atendimento (serviços e produtos, valor total) | 🗄️ | `main.py` `concluir_atendimento` | Funciona. Grava uma linha por item. Serviço e produto compartilham o campo `id_item` e os ids colidem |
| Cadastro de produtos | 🗄️ | Apenas no banco | Sem tela. Produtos são vendidos junto com o atendimento |
| Lista de agendamentos | 🗄️ | `agendamento.py` | Lê de um Google Forms/Sheets. Não usa o banco |
| Criar agendamento pelo app | 🗄️ | `main.py` `criar_novo_agendamento` | **Incompleto**: botão "Agendar" sem ação |
| Aviso de aniversariantes na tela | 🗄️ | `main.py` `lembrete_aniversario` | **Incompleto**: não exibe nada |
| E-mail de aniversário | 🗄️ | `EnvioEmail.py` | Bug: para no primeiro cliente que não faz aniversário (`return` dentro do loop). Credenciais SMTP agora vêm das variáveis `EMAIL_REMETENTE` e `EMAIL_SENHA_APP` |

## 6. Decisões registradas

| Data | Decisão |
|---|---|
| 2026-09-30 | Nome do app: **Martinho**. Identidade visual em azul, branco e dourado |
| 2026-09-30 | Produtos ficam fora do MVP (o `ItemAtendimento` já comporta produtos no futuro) |
| 2026-09-30 | Os dados do `barbearia.db` são de teste: **não haverá importação** do legado |
| 2026-09-30 | O código Tkinter vai para `legacy/` e o `barbearia.db` sai do Git |
| 2026-09-30 | Identidade visual: Bodoni Moda + Figtree; dourado só como detalhe; tema claro e escuro |
| 2026-09-30 | Desenvolvimento local com SQLite e sem `.env` obrigatório; PostgreSQL (Supabase) só em produção |
| 2026-09-30 | **Telas no Django clássico (templates), no lugar de React.** Um só projeto e um só deploy. Sai o Django REST Framework, o JWT e o Cloudflare Pages |
| 2026-09-30 | Agendamento online entra no MVP: cliente se identifica só com nome e telefone, agendamento confirmado na hora, cliente sempre escolhe o barbeiro |
| 2026-09-30 | Página do cliente muda para dia → barbeiros daquele dia → horário. Ausência pode ser de parte do dia. Aviso ao barbeiro por push do PWA (grátis); WhatsApp automático fica de fora por custo (API oficial paga) ou risco de banimento (soluções não oficiais) |
| 2026-10-02 | Migração para Next.js + Supabase (RLS, multi-tenant) feita e **desfeita** no mesmo dia: a curva de aprendizado não compensava agora. O código ficou guardado no branch `nextjs` para uma retomada futura (por exemplo, com várias barbearias) |
| 2026-10-03 | Hospedagem do Django muda do Render para a Vercel (plano Hobby, gratuito), com o mesmo banco no Supabase. O dono está ciente de que os termos do plano Hobby permitem só uso não comercial (o Pro custa US$ 20/mês) |
| 2026-10-03 | Código do desktop Tkinter (`legacy/`) removido do repositório; fica no histórico do git |

## 7. Fora do MVP (ideias futuras)

- Venda e estoque de produtos
- Cliente desmarcar o próprio horário pela página (hoje ele fala com a barbearia pelo WhatsApp)
- Barbeiro logado ver só a própria agenda
- Relatórios financeiros

## 8. Histórico de alterações

| Data | Alteração |
|---|---|
| 2026-09-30 | Criação do documento a partir da análise do sistema legado e do escopo do MVP |
| 2026-09-30 | Nome definido como Martinho; decisões sobre produtos, importação e legado |
| 2026-09-30 | Identidade visual criada (logos, tokens, guia). Fase 0: legado movido para `legacy/`, banco fora do Git, `.gitignore` unificado |
| 2026-09-30 | Fase 1: projeto Django em `backend/` (Django 6.1, PostgreSQL obrigatório), models, admin isolado por barbearia e 13 testes |
| 2026-09-30 | Projeto simplificado: SQLite no desenvolvimento, regra de conflito movida do PostgreSQL para o Django, admin com o nome Martinho. 15 testes |
| 2026-09-30 | Banco de produção no Supabase conectado e migrado. Testes sempre em SQLite; `/` redireciona ao admin; VS Code usa a venv do back-end |
| 2026-09-30 | Telas do sistema: login, agenda do dia, novo agendamento e remarcação, clientes e ficha com histórico. Comando `dados_demo`. 30 testes |
| 2026-09-30 | Horários de trabalho e folgas, agendamento online pelo cliente, PWA. Deploy no Render: `ALLOWED_HOSTS` automático. 54 testes |
| 2026-09-30 | Primeiro deploy no Render (https://martinhoapp.onrender.com), banco de produção no Supabase. Corrigida a migration do `slug` no PostgreSQL |
| 2026-09-30 | Agenda: dia sem horários mostra os próximos agendamentos (um horário marcado pelo cliente para outro dia parecia ter sumido). 55 testes |
| 2026-09-30 | Equipe do dia e faltas na Agenda, ausência de parte do dia, página do cliente por dia com todos os barbeiros disponíveis, notificação push ao barbeiro. 80 testes |
| 2026-10-02 | Versão Next.js + Supabase criada e desfeita; guardada no branch `nextjs` |
| 2026-10-03 | Deploy preparado para a Vercel: `settings.py` reconhece a Vercel (produção, endereços liberados, banco sem conexões persistentes pelo pooler, estáticos pelo CDN). `legacy/` removida. Incluídas no documento as linhas do Balanço e do atendimento sem hora marcada, e corrigido o fluxo da página do cliente. 113 testes |
