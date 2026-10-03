import { createServerClient } from '@supabase/ssr'
import { type NextRequest, NextResponse } from 'next/server'

/**
 * Roda antes de cada página (o antigo "middleware" do Next).
 *
 * 1. Renova o login: o token do Supabase vale 1 hora. Aqui ele é trocado
 *    por um novo quando está perto de vencer, e o cookie é regravado.
 * 2. Manda para /entrar quem tenta abrir o sistema sem login.
 *
 * Isto é só a porta de entrada. A proteção dos dados é a RLS do banco:
 * mesmo que alguém passasse por aqui, sem login o banco não devolve nada.
 */

// Páginas abertas a qualquer pessoa.
const PUBLICAS = ['/entrar', '/auth', '/offline', '/agendar', '/manifest.webmanifest', '/sw.js']

export async function proxy(request: NextRequest) {
  const caminho = request.nextUrl.pathname
  // A página de agendamento do cliente não usa login: nem consulta o Auth.
  if (caminho.startsWith('/agendar/')) return NextResponse.next()

  let resposta = NextResponse.next({ request })
  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
    {
      cookies: {
        getAll: () => request.cookies.getAll(),
        setAll(lista) {
          for (const { name, value } of lista) request.cookies.set(name, value)
          resposta = NextResponse.next({ request })
          for (const { name, value, options } of lista) resposta.cookies.set(name, value, options)
        },
      },
    },
  )
  const {
    data: { user },
  } = await supabase.auth.getUser()

  const publica = PUBLICAS.some((p) => caminho === p || caminho.startsWith(`${p}/`))
  if (!user && !publica && !caminho.startsWith('/api/')) {
    const entrar = request.nextUrl.clone()
    entrar.pathname = '/entrar'
    entrar.search = caminho === '/' ? '' : `?proximo=${encodeURIComponent(caminho + request.nextUrl.search)}`
    return NextResponse.redirect(entrar)
  }
  return resposta
}

export const config = {
  // Não roda para arquivos estáticos (CSS, JS, imagens).
  matcher: ['/((?!_next/static|_next/image|img/|favicon.ico|.*\\.(?:svg|png|jpg|ico)$).*)'],
}
