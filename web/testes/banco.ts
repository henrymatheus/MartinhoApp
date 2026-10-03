/**
 * Banco de teste: um PostgreSQL de verdade rodando em memória (PGlite),
 * sem Docker e sem tocar no Supabase.
 *
 * O Supabase traz o schema "auth" (logins) e os papéis anon,
 * authenticated e service_role. Aqui eles são recriados do jeito mínimo
 * que as migrations precisam; depois as migrations rodam em ordem, igual
 * ao `supabase db push`.
 */
import { readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { PGlite } from '@electric-sql/pglite'
import { btree_gist } from '@electric-sql/pglite/contrib/btree_gist'

const PASTA_MIGRATIONS = join(import.meta.dirname, '..', 'supabase', 'migrations')

const SUPABASE_SIMULADO = `
  create role anon nologin;
  create role authenticated nologin;
  create role service_role nologin bypassrls;
  create schema auth;
  grant usage on schema auth to anon, authenticated, service_role;
  create table auth.users (id uuid primary key default gen_random_uuid(), email text);
  -- Igual ao Supabase: o id do usuário logado vem do token (JWT).
  create function auth.uid() returns uuid language sql stable as $$
    select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid
  $$;
  grant execute on function auth.uid() to anon, authenticated, service_role;
  -- O Supabase dá acesso às tabelas novas para estes papéis por padrão.
  alter default privileges in schema public grant all on tables to anon, authenticated, service_role;
  alter default privileges in schema public grant all on sequences to anon, authenticated, service_role;
  grant usage on schema public to anon, authenticated, service_role;
`

export async function criarBanco() {
  const db = await PGlite.create({ extensions: { btree_gist } })
  await db.exec(SUPABASE_SIMULADO)
  for (const arquivo of readdirSync(PASTA_MIGRATIONS).filter((a) => a.endsWith('.sql')).sort()) {
    try {
      await db.exec(readFileSync(join(PASTA_MIGRATIONS, arquivo), 'utf8'))
    } catch (erro) {
      throw new Error(`Falha na migration ${arquivo}: ${(erro as Error).message}`)
    }
  }
  // Os testes comparam datas e horas no fuso da barbearia.
  await db.exec(`set timezone = 'America/Sao_Paulo'`)
  return db
}

export type Banco = Awaited<ReturnType<typeof criarBanco>>

/** Volta a ser o administrador do banco (sem RLS). */
export async function comoAdmin(db: Banco) {
  await db.exec(`reset role; select set_config('request.jwt.claim.sub', '', false);`)
}

/** Passa a agir como um usuário logado: a RLS vale a partir daqui. */
export async function comoUsuario(db: Banco, id: string) {
  await db.exec(`reset role; select set_config('request.jwt.claim.sub', '${id}', false); set role authenticated;`)
}

/** Visitante sem login (a página pública de agendamento). */
export async function comoVisitante(db: Banco) {
  await db.exec(`reset role; select set_config('request.jwt.claim.sub', '', false); set role anon;`)
}

export async function linhas<T = Record<string, unknown>>(db: Banco, sql: string, params: unknown[] = []) {
  return (await db.query<T>(sql, params)).rows
}

export async function valor<T = unknown>(db: Banco, sql: string, params: unknown[] = []) {
  const [linha] = (await db.query<Record<string, T>>(sql, params)).rows
  return linha ? Object.values(linha)[0] : undefined
}
