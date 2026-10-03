/**
 * Migração única: Django -> Next.js + Supabase.
 *
 * Uso (na pasta web/, com o .env.local preenchido):
 *   npm run migrar:django
 *
 * O que faz:
 * 1. Confere que as tabelas novas estão vazias (não roda duas vezes).
 * 2. Cria um login no Supabase Auth para cada usuário ativo do Django, com
 *    o mesmo e-mail. As senhas NÃO podem ser copiadas (o Django guarda um
 *    resumo PBKDF2 que o Supabase Auth não lê), então cada um recebe uma
 *    senha aleatória e, no fim, um link para criar a própria senha.
 * 3. Copia todos os dados numa transação só (scripts/copiar-dados.ts): se
 *    algo falhar, nada fica pela metade.
 * 4. Mostra os links de "criar senha" para enviar a cada pessoa.
 *
 * Precisa de: DATABASE_URL (conexão direta ao Postgres do Supabase, a
 * mesma que o Django usa), NEXT_PUBLIC_SUPABASE_URL, SUPABASE_SECRET_KEY e
 * NEXT_PUBLIC_SITE_URL (endereço do site novo, para os links).
 *
 * As tabelas do Django não são alteradas nem apagadas.
 */
import { randomBytes } from 'node:crypto'
import { createClient } from '@supabase/supabase-js'
import { Client } from 'pg'
import { copiarDados } from './copiar-dados'

function exigir(nome: string) {
  const valor = process.env[nome]
  if (!valor) {
    console.error(`Falta a variável ${nome} no .env.local.`)
    process.exit(1)
  }
  return valor
}

async function main() {
  const site = exigir('NEXT_PUBLIC_SITE_URL').replace(/\/$/, '')
  const admin = createClient(exigir('NEXT_PUBLIC_SUPABASE_URL'), exigir('SUPABASE_SECRET_KEY'), {
    auth: { persistSession: false, autoRefreshToken: false },
  })
  const db = new Client({ connectionString: exigir('DATABASE_URL') })
  await db.connect()
  const q = async (sql: string, params?: unknown[]) => (await db.query(sql, params)).rows

  try {
    const [{ n }] = await q('select count(*)::int as n from public.barbearias')
    if (n > 0) {
      console.error('As tabelas novas já têm dados. A migração já foi feita (ou começou a ser feita). Nada foi alterado.')
      process.exit(1)
    }

    const usuarios = (await q(
      `select id, username, lower(trim(email)) as email from contas_usuario where is_active order by id`,
    )) as { id: number; username: string; email: string }[]
    const semEmail = usuarios.filter((u) => !u.email)
    if (semEmail.length) {
      console.error('Estes usuários do Django estão sem e-mail (o login novo é por e-mail):')
      for (const u of semEmail) console.error(`  - ${u.username}`)
      console.error('Preencha o e-mail deles no /admin/ do Django e rode de novo. Nada foi alterado.')
      process.exit(1)
    }

    // Logins que já existam no Auth (de uma tentativa anterior) são reaproveitados.
    const existentes = new Map<string, string>()
    for (let pagina = 1; ; pagina++) {
      const { data } = await admin.auth.admin.listUsers({ page: pagina, perPage: 1000 })
      for (const u of data.users) if (u.email) existentes.set(u.email.toLowerCase(), u.id)
      if (data.users.length < 1000) break
    }

    const mapa: { djangoId: number; uuid: string; email: string }[] = []
    for (const u of usuarios) {
      let uuid = existentes.get(u.email)
      if (!uuid) {
        const { data, error } = await admin.auth.admin.createUser({
          email: u.email,
          password: randomBytes(24).toString('base64url'),
          email_confirm: true,
        })
        if (error || !data.user) throw new Error(`Não foi possível criar o login de ${u.email}: ${error?.message}`)
        uuid = data.user.id
      }
      mapa.push({ djangoId: u.id, uuid, email: u.email })
      console.log(`Login: ${u.username} -> ${u.email}`)
    }

    await q('begin')
    try {
      const contagens = await copiarDados(q, mapa)
      await q('commit')
      console.log('\nDados copiados:')
      for (const [tabela, total] of Object.entries(contagens)) console.log(`  ${tabela}: ${total}`)
    } catch (erro) {
      await q('rollback')
      throw erro
    }

    console.log('\nLinks para cada pessoa criar a própria senha (cada um vale uma vez):')
    for (const { email } of mapa) {
      const { data } = await admin.auth.admin.generateLink({ type: 'recovery', email })
      const token = data.properties?.hashed_token
      const link = token
        ? `${site}/auth/confirmar?${new URLSearchParams({ token_hash: token, type: 'recovery', proximo: '/conta/senha' })}`
        : '(não foi possível gerar; use "Esqueci minha senha" no login)'
      console.log(`  ${email}\n    ${link}`)
    }
    console.log('\nPronto. Os links também podem ser gerados depois no painel /admin do site novo.')
  } finally {
    await db.end()
  }
}

main().catch((erro) => {
  console.error('\nA migração falhou e nada foi gravado nas tabelas novas.')
  console.error(erro)
  process.exit(1)
})
