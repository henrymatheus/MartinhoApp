'use server'

import { revalidatePath } from 'next/cache'
import { redirect } from 'next/navigation'
import { avisar } from '@/lib/avisos'
import { lerDia } from '@/lib/datas'
import { type EstadoFormulario, inteiro, texto, valores } from '@/lib/formularios'
import { exigirBarbearia } from '@/lib/sessao'

/**
 * Registra o atendimento avulso pela função registrar_atendimento do
 * banco, que faz numa transação só: acha ou cria o cliente (pelo
 * telefone) e grava o atendimento. As regras de quem pode (o barbeiro só
 * para si) e da data (não pode ser futura) estão lá.
 */
export async function registrarAtendimento(_estado: EstadoFormulario, dados: FormData): Promise<EstadoFormulario> {
  const { supabase, ehBarbeiro } = await exigirBarbearia()
  const v = valores(dados)
  const barbeiro = inteiro(dados, 'barbeiro')
  const data = lerDia(texto(dados, 'data'))
  if (!barbeiro) return { erros: { barbeiro: 'Escolha o barbeiro.' }, valores: v }
  if (!data) return { erros: { data: 'Informe a data.' }, valores: v }

  const { data: resultado, error } = await supabase.rpc('registrar_atendimento', {
    p_cliente: inteiro(dados, 'cliente'),
    p_novo_nome: texto(dados, 'novo_nome'),
    p_novo_telefone: texto(dados, 'novo_telefone'),
    p_barbeiro: barbeiro,
    p_data: data,
    p_observacoes: texto(dados, 'observacoes'),
  })
  // As mensagens de regra (P0001) vêm prontas do banco, em português.
  if (error) return { erro: error.code === 'P0001' || error.code === '42501' ? error.message : 'Não foi possível registrar. Tente de novo.', valores: v }

  const { data: cliente } = await supabase.from('clientes').select('nome').eq('id', resultado.cliente_id).single()
  await avisar('sucesso', `Atendimento de ${cliente?.nome ?? 'cliente'} registrado.`)
  revalidatePath('/balanco')
  // Volta para o balanço do dia do atendimento, onde ele já aparece.
  redirect(`/balanco?periodo=dia&data=${data}${ehBarbeiro ? '' : `&barbeiro=${barbeiro}`}`)
}
