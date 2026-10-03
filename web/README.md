# Martinho (Next.js + Supabase)

Nova versão do Martinho: Next.js (App Router) na Vercel, banco PostgreSQL no Supabase, isolamento entre barbearias por RLS. Substitui a versão Django, cujo código foi removido do repositório (fica no histórico do git); o Django continua no Render até a troca.

## Como o projeto está organizado

| Pasta | O que tem |
|---|---|
| `supabase/migrations/` | O banco: tabelas (`…01_esquema.sql`), RLS (`…02_rls.sql`) e as regras de agenda em funções SQL (`…03_funcoes.sql`) |
| `app/(sistema)/` | Telas com login: agenda, clientes, horários, balanço, configurações, painel do superadmin |
| `app/agendar/[slug]/` | Página pública de agendamento do cliente |
| `app/entrar/`, `app/auth/` | Login, "esqueci a senha" e o retorno dos links de e-mail |
| `lib/` | Sessão, datas no fuso de São Paulo, telefones, período do balanço, push |
| `proxy.ts` | Renova o login a cada requisição e manda para `/entrar` quem não está logado |
| `testes/` | Testes do banco (em memória, sem Docker) e das regras do app |
| `scripts/` | Migração única do Django e gerador de chaves push |

### Onde fica a segurança

1. **RLS no banco** (principal): toda tabela tem `barbearia_id` e políticas que só deixam o usuário ver e alterar as linhas da própria barbearia. O visitante sem login não lê nenhuma tabela; a página pública só chama funções `agenda_publica`, `agendar_online` e `confirmacao_publica`.
2. **Chaves compostas**: um agendamento não aponta para cliente, barbeiro ou serviço de outra barbearia; o banco recusa.
3. **Conflito de horário**: uma *exclusion constraint* impede dois agendamentos sobrepostos do mesmo barbeiro, mesmo com dois pedidos no mesmo instante.
4. **Chave secreta** (`SUPABASE_SECRET_KEY`, ignora a RLS): só em `lib/supabase/admin.ts`, marcado com `server-only`. Usada para criar logins, no painel do superadmin e no envio de push.

## Rodar localmente

Use um **segundo projeto Supabase só para desenvolvimento** (o plano gratuito permite dois), para não mexer nos dados da barbearia.

```powershell
cd web
npm install
copy .env.example .env.local   # e preencha com as chaves do projeto de desenvolvimento
npm run dev                    # http://localhost:3000
```

Para aplicar as migrations no projeto de desenvolvimento, escolha um caminho:

- **Supabase CLI**: `npx supabase login`, `npx supabase init` (aceite os padrões), `npx supabase link --project-ref <id-do-projeto>` e `npx supabase db push`.
- **Pelo painel**: SQL Editor, cole e rode os três arquivos de `supabase/migrations/` em ordem.

Primeiro login: crie um usuário em Authentication > Users (com "Auto Confirm User") e, no SQL Editor, torne-o superadmin:

```sql
insert into perfis (id, nome, superadmin) values ('<uuid do usuário>', 'Henry', true);
```

Entre no site e crie a primeira barbearia em **Administração**.

## Testes

```powershell
npm test
```

Roda um PostgreSQL de verdade em memória (PGlite) com as migrations, simulando o `auth` e os papéis do Supabase. Cobre conflito de horário, isolamento por RLS, horários livres, página pública, balanço e o ensaio da migração do Django.

## Deploy na Vercel

1. Em vercel.com, **Add New > Project**, importe o repositório do GitHub e, em **Root Directory**, escolha `web`.
2. Em **Environment Variables**, cadastre as variáveis de `.env.example` (sem a `DATABASE_URL`) com as chaves do projeto Supabase de produção. `NEXT_PUBLIC_SITE_URL` é o endereço final do site.
3. Em **Settings > Functions > Function Region**, escolha a mesma região do Supabase (São Paulo: `gru1`, se o Supabase estiver em `sa-east-1`). Banco e servidor longe um do outro deixam cada tela mais lenta.
4. No Supabase, **Authentication > URL Configuration**: `Site URL` = endereço do site; em `Redirect URLs`, adicione `https://<seu-site>/auth/confirmar` (e `http://localhost:3000/auth/confirmar` no projeto de desenvolvimento).

Cada push na branch `main` publica sozinho.

> **Atenção, plano Hobby (gratuito) da Vercel:** os termos de uso permitem só uso pessoal e não comercial. Para uso comercial o plano é o Pro.

## Troca do Django para esta versão

1. Aplique as migrations no Supabase de **produção** (mesmo banco do Django; os nomes das tabelas não colidem).
2. Confira que todo usuário ativo do Django tem e-mail (o login novo é por e-mail).
3. Na pasta `web/`, com `.env.local` apontando para produção e com a `DATABASE_URL` do Django: `npm run migrar:django`. O script copia tudo numa transação só, mantém os ids e imprime um link de "criar senha" para cada pessoa (as senhas do Django não podem ser copiadas).
4. Torne o seu login superadmin, se ainda não for (o script já marca quem era superusuário no Django).
5. Envie os links, confira a agenda no site novo e troque o link de agendamento divulgado aos clientes (bio do Instagram etc.).
6. Desligue o serviço do Render. As tabelas do Django ficam no banco até você decidir apagá-las.
