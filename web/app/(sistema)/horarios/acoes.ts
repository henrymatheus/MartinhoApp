'use server'

import { revalidatePath } from 'next/cache'
import { redirect } from 'next/navigation'
import { descreverAusencia } from '@/lib/agenda'
import { avisar } from '@/lib/avisos'
import { lerDia, lerHora, NOMES_DOS_DIAS } from '@/lib/datas'
import { type EstadoFormulario, marcado, texto, valores } from '@/lib/formularios'
import { exigirBarbearia } from '@/lib/sessao'
import type { Ausencia } from '@/lib/tipos'

const TURNOS = 2

/**
 * Os turnos da semana de um barbeiro numa tela só. Para cada dia:
 * "atende?" e até dois turnos (manhã e tarde); o intervalo é o almoço.
 * Ao salvar, os turnos antigos são trocados pelos novos (função
 * salvar_semana, numa transação). A RLS decide se o usuário pode.
 */
export async function salvarSemana(barbeiroId: number, _estado: EstadoFormulario, dados: FormData): Promise<EstadoFormulario> {
  const { supabase } = await exigirBarbearia()
  const erros: string[] = []
  const turnos: { dia_semana: number; inicio: string; fim: string }[] = []

  NOMES_DOS_DIAS.forEach((nome, dia) => {
    if (!marcado(dados, `d${dia}_ativo`)) return
    let fimAnterior: string | null = null
    for (let n = 1; n <= TURNOS; n++) {
      const inicioTexto = texto(dados, `d${dia}_inicio${n}`)
      const fimTexto = texto(dados, `d${dia}_fim${n}`)
      if (n > 1 && !inicioTexto && !fimTexto) continue // a tarde é opcional
      const inicio = lerHora(inicioTexto)
      const fim = lerHora(fimTexto)
      if (!inicio || !fim) erros.push(`${nome}: preencha o início e o fim.`)
      else if (fim <= inicio) erros.push(`${nome}: o fim precisa ser depois do início.`)
      else if (fimAnterior && inicio < fimAnterior) erros.push(`${nome}: a tarde precisa começar depois do fim da manhã.`)
      else {
        turnos.push({ dia_semana: dia, inicio, fim })
        fimAnterior = fim
      }
    }
  })
  if (erros.length) return { erro: erros.join(' '), valores: valores(dados) }

  const { error } = await supabase.rpc('salvar_semana', { p_barbeiro: barbeiroId, p_turnos: turnos })
  if (error) return { erro: 'Você não pode alterar os horários deste barbeiro.', valores: valores(dados) }
  await avisar('sucesso', 'Horários salvos.')
  revalidatePath('/horarios')
  redirect(`/horarios/${barbeiroId}`)
}

export async function adicionarAusencia(barbeiroId: number, _estado: EstadoFormulario, dados: FormData): Promise<EstadoFormulario> {
  const { supabase, barbearia } = await exigirBarbearia()
  const v = valores(dados)
  const dataInicio = lerDia(texto(dados, 'data_inicio'))
  const dataFim = lerDia(texto(dados, 'data_fim')) ?? dataInicio
  const horaInicio = texto(dados, 'hora_inicio') ? lerHora(texto(dados, 'hora_inicio')) : null
  const horaFim = texto(dados, 'hora_fim') ? lerHora(texto(dados, 'hora_fim')) : null
  const motivo = texto(dados, 'motivo').slice(0, 80)

  const erros: Record<string, string> = {}
  if (!dataInicio) erros.data_inicio = 'Informe a data.'
  else if (dataFim! < dataInicio) erros.data_fim = 'A data final precisa ser igual ou depois da inicial.'
  if (Boolean(horaInicio) !== Boolean(horaFim)) erros.hora_inicio = 'Para uma ausência de parte do dia, preencha o horário de início e o de fim.'
  else if (horaInicio && horaFim) {
    if (dataInicio !== dataFim) erros.hora_inicio = 'Ausência com horário vale para um único dia.'
    else if (horaFim <= horaInicio) erros.hora_fim = 'O fim precisa ser depois do início.'
  }
  if (Object.keys(erros).length) return { erros, valores: v }

  const { data, error } = await supabase
    .from('ausencias')
    .insert({ barbearia_id: barbearia.id, barbeiro_id: barbeiroId, data_inicio: dataInicio, data_fim: dataFim, hora_inicio: horaInicio, hora_fim: horaFim, motivo })
    .select('*')
    .single<Ausencia>()
  if (error || !data) return { erro: 'Você não pode registrar ausências para este barbeiro.', valores: v }
  await avisar('sucesso', `Ausência registrada: ${descreverAusencia(data)}.`)
  revalidatePath(`/horarios/${barbeiroId}`)
  redirect(`/horarios/${barbeiroId}`)
}

export async function removerAusencia(barbeiroId: number, id: number) {
  const { supabase } = await exigirBarbearia()
  const { data } = await supabase.from('ausencias').delete().eq('id', id).eq('barbeiro_id', barbeiroId).select('id')
  await avisar(data?.length ? 'sucesso' : 'erro', data?.length ? 'Ausência removida.' : 'Você não pode remover esta ausência.')
  revalidatePath(`/horarios/${barbeiroId}`)
  redirect(`/horarios/${barbeiroId}`)
}
