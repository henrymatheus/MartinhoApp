'use server'

import { revalidatePath } from 'next/cache'
import { redirect } from 'next/navigation'
import { avisar } from '@/lib/avisos'
import { lerDia } from '@/lib/datas'
import { type EstadoFormulario, EMAIL_VALIDO, texto, valores } from '@/lib/formularios'
import { exigirBarbearia } from '@/lib/sessao'

/** Cadastro (id = null) ou edição de cliente. */
export async function salvarCliente(id: number | null, _estado: EstadoFormulario, dados: FormData): Promise<EstadoFormulario> {
  const { supabase, barbearia } = await exigirBarbearia()
  const v = valores(dados)
  const linha = {
    nome: texto(dados, 'nome').replace(/\s+/g, ' '),
    telefone: texto(dados, 'telefone'),
    email: texto(dados, 'email').toLowerCase(),
    data_nascimento: texto(dados, 'data_nascimento') || null,
    endereco: texto(dados, 'endereco'),
    observacoes: texto(dados, 'observacoes'),
  }
  const erros: Record<string, string> = {}
  if (!linha.nome) erros.nome = 'Informe o nome.'
  else if (linha.nome.length > 120) erros.nome = 'Use no máximo 120 caracteres.'
  if (linha.telefone.length > 20) erros.telefone = 'Use no máximo 20 caracteres.'
  if (linha.email && !EMAIL_VALIDO.test(linha.email)) erros.email = 'Informe um e-mail válido.'
  if (linha.data_nascimento && !lerDia(linha.data_nascimento)) erros.data_nascimento = 'Data inválida.'
  if (linha.endereco.length > 255) erros.endereco = 'Use no máximo 255 caracteres.'
  if (Object.keys(erros).length) return { erros, valores: v }

  // A barbearia vem da sessão, não do formulário: o usuário não escolhe.
  // E mesmo que tentasse outra, a RLS recusaria a gravação.
  const { data, error } = id
    ? await supabase.from('clientes').update(linha).eq('id', id).select('id').single()
    : await supabase.from('clientes').insert({ ...linha, barbearia_id: barbearia.id }).select('id').single()
  if (error || !data) return { erro: 'Não foi possível salvar. Tente de novo.', valores: v }

  await avisar('sucesso', id ? 'Dados do cliente atualizados.' : `${linha.nome} cadastrado.`)
  revalidatePath('/clientes')
  redirect(`/clientes/${data.id}`)
}
