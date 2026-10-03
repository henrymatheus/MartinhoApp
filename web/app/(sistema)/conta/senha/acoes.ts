'use server'

import type { EstadoFormulario } from '@/lib/formularios'
import { exigirLogin } from '@/lib/sessao'

export async function trocarSenha(_estado: EstadoFormulario, dados: FormData): Promise<EstadoFormulario> {
  const sessao = await exigirLogin()
  const senha = String(dados.get('senha') ?? '')
  if (senha.length < 8) return { erros: { senha: 'A senha precisa ter pelo menos 8 caracteres.' } }
  if (senha !== dados.get('confirmacao')) return { erros: { confirmacao: 'As duas senhas não são iguais.' } }
  const { error } = await sessao.supabase.auth.updateUser({ password: senha })
  if (error) return { erro: 'Não foi possível trocar a senha. Tente uma senha diferente.' }
  return { ok: 'Senha salva. Use a nova senha no próximo login.' }
}
