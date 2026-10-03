/**
 * Datas e horas no fuso da barbearia (São Paulo).
 *
 * O servidor da Vercel roda em UTC. Se usássemos new Date() direto, um
 * horário às 22:00 de segunda apareceria como terça (01:00 UTC). Por isso
 * toda conversão entre "instante" e "dia/hora na barbearia" passa por aqui.
 *
 * Convenções:
 * - Dia: texto 'AAAA-MM-DD' (o mesmo formato do <input type="date">).
 * - Hora: texto 'HH:MM'.
 * - Instante: Date (ou texto ISO vindo do banco).
 */

export const FUSO = 'America/Sao_Paulo'

const formatoDia = new Intl.DateTimeFormat('en-CA', { timeZone: FUSO, year: 'numeric', month: '2-digit', day: '2-digit' })
const formatoHora = new Intl.DateTimeFormat('pt-BR', { timeZone: FUSO, hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })
const formatoDeslocamento = new Intl.DateTimeFormat('en-US', { timeZone: FUSO, timeZoneName: 'longOffset' })

const comoData = (instante: Date | string) => (typeof instante === 'string' ? new Date(instante) : instante)

/** O dia (AAAA-MM-DD) de um instante, no fuso da barbearia. */
export function diaLocal(instante: Date | string): string {
  return formatoDia.format(comoData(instante))
}

/** A hora (HH:MM) de um instante, no fuso da barbearia. */
export function horaLocal(instante: Date | string): string {
  return formatoHora.format(comoData(instante))
}

export function hojeLocal(agora: Date = new Date()): string {
  return diaLocal(agora)
}

/** Lê um dia vindo da URL ou de um formulário; texto inválido vira null. */
export function lerDia(texto: unknown): string | null {
  if (typeof texto !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(texto)) return null
  const data = new Date(`${texto}T12:00:00Z`)
  return Number.isNaN(data.getTime()) || data.toISOString().slice(0, 10) !== texto ? null : texto
}

export function lerHora(texto: unknown): string | null {
  if (typeof texto !== 'string') return null
  const m = /^([01]\d|2[0-3]):([0-5]\d)(:00)?$/.exec(texto)
  return m ? `${m[1]}:${m[2]}` : null
}

export function somarDias(dia: string, dias: number): string {
  const data = new Date(`${dia}T12:00:00Z`)
  data.setUTCDate(data.getUTCDate() + dias)
  return data.toISOString().slice(0, 10)
}

export function diferencaEmDias(de: string, ate: string): number {
  return Math.round((Date.parse(`${ate}T12:00:00Z`) - Date.parse(`${de}T12:00:00Z`)) / 86_400_000)
}

/** 0 = segunda ... 6 = domingo (mesma numeração do banco e do Django). */
export function diaDaSemana(dia: string): number {
  return (new Date(`${dia}T12:00:00Z`).getUTCDay() + 6) % 7
}

/**
 * "Dia + hora na barbearia" -> instante. O deslocamento (-03:00) é
 * consultado para aquela data, então continua certo se o horário de
 * verão voltar a existir.
 */
export function instante(dia: string, hora: string): Date {
  const parte = formatoDeslocamento.formatToParts(new Date(`${dia}T12:00:00Z`)).find((p) => p.type === 'timeZoneName')
  const deslocamento = parte?.value.replace('GMT', '') || '+00:00'
  return new Date(`${dia}T${hora}:00${deslocamento === '' ? 'Z' : deslocamento}`)
}

// ---------- Textos para a tela ----------

const MESES = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
const MESES_CURTOS = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
const SEMANA = ['segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira', 'sábado', 'domingo']
const SEMANA_CURTA = ['seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom']
export const NOMES_DOS_DIAS = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']

const partes = (dia: string) => {
  const [ano, mes, d] = dia.split('-').map(Number)
  return { ano, mes, d }
}

/** "segunda-feira" */
export const nomeDoDia = (dia: string) => SEMANA[diaDaSemana(dia)]
/** "seg" */
export const nomeCurtoDoDia = (dia: string) => SEMANA_CURTA[diaDaSemana(dia)]
/** "out" */
export const mesCurto = (dia: string) => MESES_CURTOS[partes(dia).mes - 1]
/** "outubro" */
export const nomeDoMes = (dia: string) => MESES[partes(dia).mes - 1]

/** "5 de outubro" */
export function diaEMes(dia: string): string {
  const { mes, d } = partes(dia)
  return `${d} de ${MESES[mes - 1]}`
}

/** "segunda-feira, 5 de outubro" */
export function diaPorExtenso(dia: string): string {
  return `${nomeDoDia(dia)}, ${diaEMes(dia)}`
}

/** "05/10" */
export function ddmm(dia: string): string {
  const { mes, d } = partes(dia)
  return `${String(d).padStart(2, '0')}/${String(mes).padStart(2, '0')}`
}

/** "05/10/2026" */
export function ddmmaaaa(dia: string): string {
  return `${ddmm(dia)}/${partes(dia).ano}`
}

/** Primeira letra maiúscula: "Segunda-feira, 5 de outubro". */
export function maiuscula(texto: string): string {
  return texto.charAt(0).toUpperCase() + texto.slice(1)
}
