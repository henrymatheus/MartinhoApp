'use server'

/**
 * Ações dos botões da Agenda: Concluir, Faltou, Cancelar, "Faltou hoje",
 * "Saiu agora" e "Desfazer ausência".
 *
 * Todas usam o cliente do usuário, então a RLS decide o que pode: um id de
 * agendamento de outra barbearia simplesmente não é encontrado.
 */
import { revalidatePath } from 'next/cache'
import { redirect } from 'next/navigation'
import { intervaloDaAusencia, sobrepoe } from '@/lib/agenda'
import { avisar } from '@/lib/avisos'
import { diaLocal, hojeLocal, horaLocal, lerDia } from '@/lib/datas'
import { exigirBarbearia } from '@/lib/sessao'
import { NOMES_STATUS, type Ausencia, type Status } from '@/lib/tipos'

const urlDoDia = (dia: string) => `/?data=${dia}`

export async function mudarStatus(id: number, acao: 'concluir' | 'cancelar' | 'faltou') {
  const { supabase } = await exigirBarbearia()
  const { data: ag } = await supabase.from('agendamentos').select('status, inicio, cliente:clientes(nome)').eq('id', id).maybeSingle()
  if (!ag) redirect('/')
  const dia = diaLocal(ag.inicio)
  const cliente = (ag.cliente as unknown as { nome: string }).nome

  if (ag.status !== 'agendado') {
    await avisar('erro', `Este agendamento já está como "${NOMES_STATUS[ag.status as Status]}".`)
  } else if (acao === 'concluir') {
    // Uma função do banco faz as duas coisas numa transação: muda o status
    // e grava o atendimento no histórico com o preço atual do serviço.
    const { error } = await supabase.rpc('concluir_agendamento', { p_agendamento: id })
    await avisar(error ? 'erro' : 'sucesso', error ? error.message : `Atendimento de ${cliente} concluído e registrado no histórico.`)
  } else {
    // .eq('status', 'agendado'): se duas pessoas tocarem ao mesmo tempo, só
    // a primeira muda; a segunda não encontra mais a linha "agendado".
    const status = acao === 'cancelar' ? 'cancelado' : 'faltou'
    const { data } = await supabase.from('agendamentos').update({ status }).eq('id', id).eq('status', 'agendado').select('id')
    if (!data?.length) await avisar('erro', 'Este agendamento acabou de ser alterado por outra pessoa.')
    else await avisar('sucesso', acao === 'cancelar' ? `Agendamento de ${cliente} cancelado. O horário ficou livre.` : `${cliente} marcado como falta.`)
  }
  revalidatePath('/')
  redirect(urlDoDia(dia))
}

/** "Faltou" ou "Saiu agora": cria uma ausência no dia, inteira ou a partir de agora. */
export async function marcarAusencia(barbeiroId: number, diaTexto: string, modo: 'dia' | 'agora') {
  const { supabase, barbearia } = await exigirBarbearia()
  const dia = lerDia(diaTexto) ?? hojeLocal()
  const hoje = hojeLocal()
  if (dia < hoje) {
    await avisar('erro', 'Não dá para marcar ausência em um dia que já passou.')
    redirect(urlDoDia(dia))
  }
  const ausencia = {
    barbearia_id: barbearia.id,
    barbeiro_id: barbeiroId,
    data_inicio: dia,
    data_fim: dia,
    hora_inicio: null as string | null,
    hora_fim: null as string | null,
    motivo: 'Falta',
  }
  if (modo === 'agora' && dia === hoje) {
    const agora = horaLocal(new Date())
    if (agora >= '23:59') {
      await avisar('erro', 'O dia já está terminando.')
      redirect(urlDoDia(dia))
    }
    Object.assign(ausencia, { hora_inicio: agora, hora_fim: '23:59', motivo: 'Saiu mais cedo' })
  }
  // A RLS só deixa gravar se for o dono ou o próprio barbeiro.
  const { data: criada, error } = await supabase.from('ausencias').insert(ausencia).select('*').single<Ausencia>()
  const { data: barbeiro } = await supabase.from('barbeiros').select('nome').eq('id', barbeiroId).single()
  if (error || !criada) {
    await avisar('erro', 'Você não pode marcar ausência para este barbeiro.')
    redirect(urlDoDia(dia))
  }

  const [inicio, fim] = intervaloDaAusencia(criada, dia)
  // Sobreposição: começa antes do fim da ausência e termina depois do início.
  const { data: doDia } = await supabase
    .from('agendamentos')
    .select('inicio, fim')
    .eq('barbeiro_id', barbeiroId)
    .eq('status', 'agendado')
    .lt('inicio', fim.toISOString())
    .gt('fim', inicio.toISOString())
  const afetados = (doDia ?? []).filter((ag) => sobrepoe(new Date(ag.inicio), new Date(ag.fim), inicio, fim)).length

  let texto = `Ausência de ${barbeiro?.nome} registrada. Os clientes não conseguem mais agendar com ele nesse período.`
  if (afetados === 1) texto += ' Atenção: 1 horário já marcado com ele está destacado abaixo.'
  else if (afetados > 1) texto += ` Atenção: ${afetados} horários já marcados com ele estão destacados abaixo.`
  await avisar(afetados ? 'alerta' : 'sucesso', texto)
  revalidatePath('/')
  redirect(urlDoDia(dia))
}

export async function desfazerAusencia(id: number) {
  const { supabase } = await exigirBarbearia()
  const { data } = await supabase.from('ausencias').delete().eq('id', id).select('data_inicio, barbeiro:barbeiros(nome)')
  const apagada = data?.[0]
  if (!apagada) {
    await avisar('erro', 'Você não pode desfazer esta ausência.')
    redirect('/')
  }
  await avisar('sucesso', `Ausência de ${(apagada.barbeiro as unknown as { nome: string }).nome} desfeita.`)
  revalidatePath('/')
  redirect(urlDoDia(apagada.data_inicio))
}
