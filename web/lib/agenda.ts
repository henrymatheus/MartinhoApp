/**
 * Regras da agenda interna que só servem para a tela (o que destacar, que
 * texto mostrar). As regras que protegem os dados (conflito, RLS) estão
 * no banco; estas são funções puras, testadas em testes/agenda.test.ts.
 */
import { ddmm, diaDaSemana, diaLocal, horaLocal, instante, somarDias } from './datas'
import { primeiroNome } from './telefones'
import type { Ausencia, HorarioTrabalho } from './tipos'

/** '09:00:00' (formato do Postgres) -> '09:00' */
export const hhmm = (hora: string) => hora.slice(0, 5)

/** Dois trechos se sobrepõem se um começa antes de o outro terminar, e vice-versa. */
export function sobrepoe(inicioA: Date, fimA: Date, inicioB: Date, fimB: Date) {
  return inicioA < fimB && fimA > inicioB
}

export const ehParcial = (a: Pick<Ausencia, 'hora_inicio'>) => a.hora_inicio !== null

/** O trecho em que o barbeiro está ausente naquele dia. Dia inteiro = da meia-noite à meia-noite seguinte. */
export function intervaloDaAusencia(a: Ausencia, dia: string): [Date, Date] {
  if (a.hora_inicio && a.hora_fim) return [instante(dia, hhmm(a.hora_inicio)), instante(dia, hhmm(a.hora_fim))]
  return [instante(dia, '00:00'), instante(somarDias(dia, 1), '00:00')]
}

const valeNoDia = (a: Ausencia, dia: string) => a.data_inicio <= dia && dia <= a.data_fim

/** O barbeiro está ausente em algum momento entre inicio e fim? */
export function ausenteEm(ausencias: Ausencia[], barbeiroId: number, inicio: Date, fim: Date): boolean {
  const dia = diaLocal(inicio)
  return ausencias.some((a) => {
    if (a.barbeiro_id !== barbeiroId || !valeNoDia(a, dia)) return false
    const [ai, af] = intervaloDaAusencia(a, dia)
    return sobrepoe(inicio, fim, ai, af)
  })
}

/** Texto de uma ausência: "05/10/2026, das 13:00 às 18:00", "05/10/2026" ou "05/10 a 12/10/2026". */
export function descreverAusencia(a: Ausencia): string {
  const ano = (dia: string) => `${ddmm(dia)}/${dia.slice(0, 4)}`
  if (a.hora_inicio && a.hora_fim) return `${ano(a.data_inicio)}, das ${hhmm(a.hora_inicio)} às ${hhmm(a.hora_fim)}`
  if (a.data_inicio === a.data_fim) return ano(a.data_inicio)
  return `${ddmm(a.data_inicio)} a ${ano(a.data_fim)}`
}

export type Situacao = 'atendendo' | 'parcial' | 'ausente' | 'folga'

/**
 * Situação de um barbeiro no dia, para a faixa "Equipe do dia" da agenda:
 * atendendo, ausente (dia inteiro ou parte) ou sem expediente.
 */
export function situacaoNoDia(horarios: HorarioTrabalho[], ausencias: Ausencia[], dia: string) {
  const turnos = horarios.filter((h) => h.dia_semana === diaDaSemana(dia)).sort((a, b) => a.inicio.localeCompare(b.inicio))
  const doDia = ausencias.filter((a) => valeNoDia(a, dia))
  const diaInteiro = doDia.find((a) => !ehParcial(a))
  const parciais = doDia.filter(ehParcial)
  let situacao: Situacao
  let texto: string
  if (diaInteiro) {
    situacao = 'ausente'
    texto = diaInteiro.data_fim > dia ? `Ausente até ${ddmm(diaInteiro.data_fim)}` : 'Ausente'
    if (diaInteiro.motivo) texto += ` · ${diaInteiro.motivo}`
  } else if (!turnos.length) {
    situacao = 'folga'
    texto = 'Não atende neste dia'
  } else {
    situacao = parciais.length ? 'parcial' : 'atendendo'
    texto = turnos.map((t) => `${hhmm(t.inicio)}–${hhmm(t.fim)}`).join(', ')
    if (parciais.length) texto += ' · ausente ' + parciais.map((a) => `${hhmm(a.hora_inicio!)}–${hhmm(a.hora_fim!)}`).join(', ')
  }
  // Só ausências deste único dia podem ser desfeitas na agenda; férias de
  // vários dias se editam na tela Horários.
  const desfazer = doDia.filter((a) => a.data_inicio === dia && a.data_fim === dia)
  return { situacao, texto, desfazer }
}

interface DadosMensagem {
  barbearia: string
  cliente: string
  barbeiro: string
  servico: string
  inicio: string | Date
}

export function mensagemLembrete(m: DadosMensagem) {
  return (
    `Olá, ${primeiroNome(m.cliente)}! Lembrando do seu horário na ${m.barbearia}: ` +
    `${ddmm(diaLocal(m.inicio))} às ${horaLocal(m.inicio)}, ${m.servico.toLowerCase()} com ${m.barbeiro}.`
  )
}

export function mensagemAusencia(m: DadosMensagem) {
  return (
    `Olá, ${primeiroNome(m.cliente)}! Aqui é da ${m.barbearia}. ` +
    `O ${m.barbeiro} não vai poder atender no seu horário de ${ddmm(diaLocal(m.inicio))} às ${horaLocal(m.inicio)}. ` +
    'Podemos remarcar ou passar para outro barbeiro?'
  )
}

/** Aniversário no dia (compara dia e mês). */
export function aniversarioEm(nascimento: string | null, dia: string) {
  return nascimento !== null && nascimento.slice(5, 10) === dia.slice(5, 10)
}

export const MENSAGEM_CONFLITO = 'Esse barbeiro já tem um agendamento nesse horário.'
