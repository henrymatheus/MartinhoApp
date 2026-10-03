import 'server-only'
import { redirect } from 'next/navigation'
import { cache } from 'react'
import { clienteDoUsuario } from './supabase/servidor'
import type { Barbearia, Barbeiro, Perfil } from './tipos'

/**
 * Quem está usando o sistema: o login, o perfil (barbearia e papel) e o
 * barbeiro ligado ao login, se houver.
 *
 * Equivale ao DaBarbeariaMixin do Django. A diferença: lá era ele que
 * filtrava as consultas por barbearia; aqui quem filtra é a RLS do banco.
 * A sessão serve para a tela saber o que mostrar (menu, botões do dono).
 *
 * cache(): a sessão é lida uma vez por requisição, mesmo que o layout e a
 * página peçam.
 */
export const obterSessao = cache(async () => {
  const supabase = await clienteDoUsuario()
  // getUser() confere o token com o Supabase Auth (não confia só no cookie).
  const {
    data: { user },
  } = await supabase.auth.getUser()
  if (!user) return null

  const { data: perfil } = await supabase.from('perfis').select('id, barbearia_id, nome, papel, superadmin').eq('id', user.id).maybeSingle<Perfil>()
  let barbearia: Barbearia | null = null
  let meuBarbeiro: Barbeiro | null = null
  if (perfil?.barbearia_id) {
    const [b, m] = await Promise.all([
      supabase.from('barbearias').select('*').eq('id', perfil.barbearia_id).maybeSingle<Barbearia>(),
      supabase.from('barbeiros').select('*').eq('usuario_id', user.id).maybeSingle<Barbeiro>(),
    ])
    barbearia = b.data
    meuBarbeiro = m.data
  }
  return {
    supabase,
    usuarioId: user.id,
    email: user.email ?? '',
    perfil,
    barbearia,
    meuBarbeiro,
    ehDono: perfil?.papel === 'dono' && barbearia !== null,
    ehBarbeiro: perfil?.papel === 'barbeiro',
    ehSuperadmin: perfil?.superadmin === true,
  }
})

export type Sessao = NonNullable<Awaited<ReturnType<typeof obterSessao>>>
export type SessaoDaBarbearia = Sessao & { barbearia: Barbearia; perfil: Perfil }

export async function exigirLogin(): Promise<Sessao> {
  const sessao = await obterSessao()
  if (!sessao) redirect('/entrar')
  return sessao
}

/** Telas da barbearia. Sem barbearia: o superadmin vai ao painel; os outros veem um aviso. */
export async function exigirBarbearia(): Promise<SessaoDaBarbearia> {
  const sessao = await exigirLogin()
  if (!sessao.barbearia || !sessao.perfil) redirect(sessao.ehSuperadmin ? '/admin' : '/sem-barbearia')
  return sessao as SessaoDaBarbearia
}

export async function exigirDono(): Promise<SessaoDaBarbearia> {
  const sessao = await exigirBarbearia()
  if (!sessao.ehDono) redirect('/')
  return sessao
}

export async function exigirSuperadmin(): Promise<Sessao> {
  const sessao = await exigirLogin()
  if (!sessao.ehSuperadmin) redirect('/')
  return sessao
}

/**
 * Barbeiros cujos horários e ausências o usuário pode editar: o dono, os
 * de todos; o barbeiro, só os próprios. A RLS garante o mesmo no banco;
 * aqui serve para a tela mostrar só os botões que vão funcionar.
 */
export function podeEditarBarbeiro(sessao: SessaoDaBarbearia, barbeiroId: number): boolean {
  return sessao.ehDono || sessao.meuBarbeiro?.id === barbeiroId
}
