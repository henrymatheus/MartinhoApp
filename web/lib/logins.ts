import 'server-only'
import { urlDoSite } from './site'
import { clienteAdmin } from './supabase/admin'
import type { Papel } from './tipos'

/**
 * Criação de logins (Supabase Auth + perfil). Usa o cliente admin porque
 * criar um usuário no Auth exige a chave secreta. Quem chama (Configurações
 * do dono ou o painel do superadmin) já conferiu a permissão e define a
 * barbearia a partir da sessão, nunca do formulário.
 */

/** "Barbearia do João" -> "barbearia-do-joao" */
export function gerarSlug(nome: string): string {
  return (
    nome
      .normalize('NFD')
      .replace(/[̀-ͯ]/g, '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 50)
      .replace(/-+$/, '') || 'barbearia'
  )
}

export const SLUG_VALIDO = /^[a-z0-9]+(-[a-z0-9]+)*$/

export async function criarLogin(dados: { email: string; senha: string; nome: string; barbeariaId: number | null; papel: Papel }) {
  const admin = clienteAdmin()
  const { data, error } = await admin.auth.admin.createUser({
    email: dados.email,
    password: dados.senha,
    // O dono ou o superadmin cadastrou: não precisa confirmar o e-mail.
    email_confirm: true,
  })
  if (error || !data.user) {
    const jaExiste = error?.message?.toLowerCase().includes('already')
    return { erro: jaExiste ? 'Já existe um login com este e-mail.' : 'Não foi possível criar o login.' }
  }
  const { error: erroPerfil } = await admin
    .from('perfis')
    .insert({ id: data.user.id, barbearia_id: dados.barbeariaId, nome: dados.nome, papel: dados.papel })
  if (erroPerfil) {
    // Sem perfil o login não serve para nada: desfaz.
    await admin.auth.admin.deleteUser(data.user.id)
    return { erro: 'Não foi possível criar o login.' }
  }
  return { id: data.user.id }
}

/**
 * Link de uso único para a pessoa criar a própria senha (usado para os
 * logins migrados do Django, cujas senhas não podem ser aproveitadas, e
 * para quem esqueceu a senha e não recebe o e-mail).
 */
export async function linkParaDefinirSenha(email: string) {
  const { data, error } = await clienteAdmin().auth.admin.generateLink({ type: 'recovery', email })
  if (error || !data.properties?.hashed_token) return null
  return `${await urlDoSite()}/auth/confirmar?${new URLSearchParams({
    token_hash: data.properties.hashed_token,
    type: 'recovery',
    proximo: '/conta/senha',
  })}`
}
