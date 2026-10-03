import 'server-only'
import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'
import { variavel } from '../ambiente'

/**
 * Cliente do Supabase com o login de quem está usando o sistema.
 *
 * Usa a chave pública (publishable/anon) + o token do usuário, que fica num
 * cookie. Todas as consultas feitas com ele passam pela RLS: o banco só
 * devolve linhas da barbearia do usuário. É o cliente usado em quase todo
 * o app.
 */
export async function clienteDoUsuario() {
  const cookieStore = await cookies()
  return createServerClient(variavel('NEXT_PUBLIC_SUPABASE_URL'), variavel('NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY'), {
    cookies: {
      getAll: () => cookieStore.getAll(),
      setAll(lista) {
        // Em Server Components não dá para gravar cookies; o proxy.ts já
        // renova o token a cada requisição, então aqui pode ser ignorado.
        try {
          for (const { name, value, options } of lista) cookieStore.set(name, value, options)
        } catch {}
      },
    },
  })
}
