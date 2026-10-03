import type { EmailOtpType } from '@supabase/supabase-js'
import { type NextRequest, NextResponse } from 'next/server'
import { clienteDoUsuario } from '@/lib/supabase/servidor'

/**
 * Destino dos links enviados por e-mail (nova senha) e dos links gerados
 * no painel do superadmin. O link traz um código de uso único; aqui ele é
 * trocado por um login, e a pessoa segue para a tela de criar senha.
 *
 * Dois formatos, conforme quem gerou o link:
 *   ?code=...                        e-mail "esqueci a senha" (fluxo PKCE)
 *   ?token_hash=...&type=recovery    link gerado pelo painel
 */
export async function GET(pedido: NextRequest) {
  const url = pedido.nextUrl
  const proximo = url.searchParams.get('proximo') ?? '/conta/senha'
  const destino = new URL(proximo.startsWith('/') && !proximo.startsWith('//') ? proximo : '/', url.origin)
  const supabase = await clienteDoUsuario()

  const code = url.searchParams.get('code')
  const tokenHash = url.searchParams.get('token_hash')
  const tipo = url.searchParams.get('type') as EmailOtpType | null

  const { error } = code
    ? await supabase.auth.exchangeCodeForSession(code)
    : tokenHash && tipo
      ? await supabase.auth.verifyOtp({ token_hash: tokenHash, type: tipo })
      : { error: new Error('Link incompleto') }

  if (error) return NextResponse.redirect(new URL('/entrar/esqueci?expirado=1', url.origin))
  return NextResponse.redirect(destino)
}
