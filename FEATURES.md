# Martinho — Funcionalidades

> **Regra do projeto:** este arquivo é a fonte da verdade sobre o que o sistema faz.
> Consulte-o **antes de iniciar qualquer tarefa** e atualize-o **sempre que uma funcionalidade for criada, alterada ou removida**.

Legenda de status: ✅ pronto · 🚧 em andamento · 📋 planejado · 🗄️ legado (desktop Tkinter)

Situação atual: itens 1 a 6 têm models, admin e testes (fase 1). Falta a API (fase 2) e as telas (fase 4).

Última atualização: 2026-09-30

---

## 1. Visão geral

Sistema de gestão para barbearias. Nome do app: **Martinho**. Cobre agendamento, cadastro de clientes e histórico de atendimentos.
Está migrando de um app desktop (Python + Tkinter + SQLite) para um app web (Django REST + React PWA).
A primeira barbearia cliente usará o sistema comercialmente desde o início.

## 2. Arquitetura alvo (custo zero)

| Camada | Tecnologia | Hospedagem |
|---|---|---|
| API | Django + Django REST Framework, JWT (simplejwt), WhiteNoise | Render (plano gratuito) |
| Banco | PostgreSQL | Supabase (plano gratuito). O Postgres do Render **não** será usado, pois expira em 30 dias |
| Arquivos e fotos | Supabase Storage | O disco do Render gratuito é apagado a cada deploy |
| Front-end | React + Vite + TypeScript + Tailwind + shadcn/ui (PWA) | Cloudflare Pages |
| Tarefas agendadas | GitHub Actions: e-mail de aniversário diário e backup diário com `pg_dump` | GitHub |
| Notificações | Links `wa.me` do WhatsApp (sem API paga) | — |

Regras fixas:
- Segredos ficam sempre em `.env`, nunca no Git.
- Deploy automático a partir do GitHub.
- O front mostra uma tela de "carregando" amigável enquanto a API acorda, porque o Render hiberna após 15 minutos sem uso.

## 3. Identidade visual

- Nome: **Martinho**. Símbolo: um M cortado por uma lâmina dourada.
- Cores: azul-marinho, azul, branco e detalhes em dourado, com tema claro e escuro.
- Fontes: Bodoni Moda (marca e títulos) e Figtree (interface).
- Arquivos e tokens: [docs/marca/](docs/marca/). Guia completo: https://claude.ai/artifact/DBGPR6HYLjxbw6tM4uJdz7
- Componentes definidos no guia: Button, Input, StatusBadge, AppointmentCard e LoadingScreen.

## 4. Funcionalidades do MVP (web)

| # | Funcionalidade | Status | Observações |
|---|---|---|---|
| 1 | Cadastro de barbearia | 🚧 | Base multi-barbearia: cada registro pertence a uma barbearia |
| 2 | Cadastro de barbeiros | 🚧 | |
| 3 | Cadastro de serviços (nome, preço, duração) | 🚧 | Nome único por barbearia |
| 4 | Cadastro de clientes | 🚧 | Nome, telefone, e-mail, data de nascimento, endereço |
| 5 | Agendamento | 🚧 | Conflito de horário barrado no PostgreSQL (`ExclusionConstraint`); horários encostados e cancelados não conflitam; fim calculado pela duração do serviço |
| 6 | Histórico de atendimentos por cliente | 🚧 | Serviço, barbeiro, data e observações. O item guarda cópia do preço |
| 7 | Painel com os atendimentos do dia | 📋 | |
| 8 | E-mail de aniversário | 📋 | Management command rodado diariamente pelo GitHub Actions |
| 9 | Login (JWT) | 📋 | |
| 10 | Notificação ao cliente via WhatsApp (`wa.me`) | 📋 | |
| 11 | Backup diário do banco | 📋 | `pg_dump` pelo GitHub Actions |
| 12 | Tela de "carregando" enquanto a API acorda | 📋 | |

## 5. Funcionalidades do sistema legado (desktop Tkinter)

Funcionalidades existentes em `legacy/main.py`, `legacy/agendamento.py` e `legacy/EnvioEmail.py`, que servem de referência para a migração.

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

## 7. Fora do MVP (ideias futuras)

- Venda e estoque de produtos
- Relatórios financeiros
- Agendamento online feito pelo próprio cliente

## 8. Histórico de alterações

| Data | Alteração |
|---|---|
| 2026-09-30 | Criação do documento a partir da análise do sistema legado e do escopo do MVP |
| 2026-09-30 | Nome definido como Martinho; decisões sobre produtos, importação e legado |
| 2026-09-30 | Identidade visual criada (logos, tokens, guia). Fase 0: legado movido para `legacy/`, banco fora do Git, `.gitignore` unificado |
| 2026-09-30 | Fase 1: projeto Django em `backend/` (Django 6.1, PostgreSQL obrigatório), models, admin isolado por barbearia e 13 testes |
