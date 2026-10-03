'use server'

import { redirect } from 'next/navigation'
import { type EstadoFormulario, EMAIL_VALIDO, texto } from '@/lib/formularios'
import { urlDoSite } from '@/lib/site'
import { clienteDoUsuario } from '@/lib/supabase/servidor'

/** Só aceita voltar para um endereço do próprio site (evita "open redirect"). */
function destinoSeguro(proximo: string) {
  return proximo.startsWith('/') && !proximo.startsWith('//') ? proximo : '/'
}

export async function entrar(_estado: EstadoFormulario, dados: FormData): Promise<EstadoFormulario> {
  const email = texto(dados, 'email').toLowerCase()
  const senha = String(dados.get('senha') ?? '')
  const supabase = await clienteDoUsuario()
  // O Supabase Auth confere a senha e grava o login em cookies (via setAll).
  const { error } = await supabase.auth.signInWithPassword({ email, password: senha })
  if (error) return { erro: 'E-mail ou senha incorretos. Confira e tente de novo.', valores: { email } }
  redirect(destinoSeguro(texto(dados, 'proximo')))
}

export async function sair() {
  const supabase = await clienteDoUsuario()
  await supabase.auth.signOut()
  redirect('/entrar')
}

export async function esqueciASenha(_estado: EstadoFormulario, dados: FormData): Promise<EstadoFormulario> {
  const email = texto(dados, 'email').toLowerCase()
  if (!EMAIL_VALIDO.test(email)) return { erros: { email: 'Informe um e-mail válido.' }, valores: { email } }
  const supabase = await clienteDoUsuario()
  // O e-mail leva um link para /auth/confirmar, que faz o login e abre a
  // tela de nova senha.
  await supabase.auth.resetPasswordForEmail(email, {
    redirectTo: `${await urlDoSite()}/auth/confirmar?proximo=/conta/senha`,
  })
  // Mesma resposta exista ou não o e-mail: não revela quem tem conta.
  return { ok: 'Se este e-mail tiver uma conta, você vai receber um link para criar uma nova senha.' }
}
