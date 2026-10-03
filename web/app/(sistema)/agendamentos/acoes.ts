'use server'

import { revalidatePath } from 'next/cache'
import { redirect } from 'next/navigation'
import { ausenteEm, MENSAGEM_CONFLITO } from '@/lib/agenda'
import { avisar } from '@/lib/avisos'
import { ddmm, diaLocal, horaLocal, instante, lerDia, lerHora } from '@/lib/datas'
import { type EstadoFormulario, inteiro, marcado, texto, valores } from '@/lib/formularios'
import { exigirBarbearia } from '@/lib/sessao'
import type { Ausencia } from '@/lib/tipos'

/**
 * Novo agendamento (id = null) ou remarcação.
 *
 * O conflito de horário não é verificado aqui: quem recusa é o banco
 * (exclusion constraint), inclusive se duas pessoas gravarem ao mesmo
 * tempo. Aqui só traduzimos o erro 23P01 numa mensagem.
 */
export async function salvarAgendamento(id: number | null, _estado: EstadoFormulario, dados: FormData): Promise<EstadoFormulario> {
  const { supabase, barbearia } = await exigirBarbearia()
  const v = valores(dados)
  const cliente = inteiro(dados, 'cliente')
  const barbeiro = inteiro(dados, 'barbeiro')
  const servico = inteiro(dados, 'servico')
  const dia = lerDia(texto(dados, 'data'))
  const hora = lerHora(texto(dados, 'hora'))

  const erros: Record<string, string> = {}
  if (!cliente) erros.cliente = 'Escolha o cliente.'
  if (!barbeiro) erros.barbeiro = 'Escolha o barbeiro.'
  if (!servico) erros.servico = 'Escolha o serviço.'
  if (!dia) erros.data = 'Informe a data.'
  if (!hora) erros.hora = 'Informe a hora.'
  if (Object.keys(erros).length) return { erros, valores: v }

  const inicio = instante(dia!, hora!)
  // A barbearia pode agendar com um barbeiro ausente (um encaixe, por
  // exemplo), mas precisa confirmar de propósito.
  if (!marcado(dados, 'agendar_mesmo_assim')) {
    const [{ data: s }, { data: ausencias }, { data: b }] = await Promise.all([
      supabase.from('servicos').select('duracao_minutos').eq('id', servico!).single(),
      supabase.from('ausencias').select('*').eq('barbeiro_id', barbeiro!).lte('data_inicio', dia!).gte('data_fim', dia!),
      supabase.from('barbeiros').select('nome').eq('id', barbeiro!).single(),
    ])
    const fim = new Date(inicio.getTime() + (s?.duracao_minutos ?? 0) * 60_000)
    if (ausenteEm((ausencias ?? []) as Ausencia[], barbeiro!, inicio, fim)) {
      return {
        erro: `${b?.nome} está ausente nesse horário. Escolha outro barbeiro ou horário, ou marque "Agendar mesmo assim".`,
        valores: v,
        extra: { ausencia: true },
      }
    }
  }

  const linha = {
    cliente_id: cliente!,
    barbeiro_id: barbeiro!,
    servico_id: servico!,
    inicio: inicio.toISOString(),
    observacoes: texto(dados, 'observacoes'),
  }
  // O fim não é enviado: um gatilho no banco calcula pela duração do
  // serviço (e recalcula na remarcação).
  const { data: salvo, error } = id
    ? await supabase.from('agendamentos').update(linha).eq('id', id).select('id, cliente:clientes(nome)').single()
    : await supabase.from('agendamentos').insert({ ...linha, barbearia_id: barbearia.id }).select('id, cliente:clientes(nome)').single()

  if (error) {
    if (error.code === '23P01') return { erro: MENSAGEM_CONFLITO, valores: v }
    // 23503: cliente, barbeiro ou serviço de outra barbearia (chave composta).
    return { erro: 'Não foi possível salvar. Confira os dados e tente de novo.', valores: v }
  }
  const nome = (salvo.cliente as unknown as { nome: string }).nome
  await avisar('sucesso', id ? 'Agendamento atualizado.' : `Agendado: ${nome} às ${horaLocal(inicio)} de ${ddmm(diaLocal(inicio))}.`)
  revalidatePath('/')
  redirect(`/?data=${dia}`)
}
