/**
 * O período do balanço (dia, semana, mês ou datas escolhidas) e a
 * navegação entre períodos. Mesma regra da versão Django.
 */
import { diaDaSemana, diferencaEmDias, lerDia, somarDias } from './datas'

// Uma faixa personalizada maior que isto é cortada: evita uma tela com
// milhares de linhas. Para períodos longos, o CSV tem tudo.
export const MAXIMO_DIAS = 366

export type TipoPeriodo = 'dia' | 'semana' | 'mes' | 'livre'

export interface Periodo {
  tipo: TipoPeriodo
  inicio: string
  fim: string
}

const PADRAO: TipoPeriodo = 'semana'

export const primeiroDoMes = (dia: string) => `${dia.slice(0, 8)}01`

export function ultimoDoMes(dia: string): string {
  const [ano, mes] = dia.split('-').map(Number)
  const ultimo = new Date(Date.UTC(ano, mes, 0)).getUTCDate()
  return `${dia.slice(0, 8)}${String(ultimo).padStart(2, '0')}`
}

export const mesAnterior = (dia: string) => primeiroDoMes(somarDias(primeiroDoMes(dia), -1))

/** O dia, a semana (segunda a domingo) ou o mês que contém a data. */
export function doTipo(tipo: Exclude<TipoPeriodo, 'livre'>, referencia: string): Periodo {
  if (tipo === 'dia') return { tipo, inicio: referencia, fim: referencia }
  if (tipo === 'mes') return { tipo, inicio: primeiroDoMes(referencia), fim: ultimoDoMes(referencia) }
  const segunda = somarDias(referencia, -diaDaSemana(referencia))
  return { tipo: 'semana', inicio: segunda, fim: somarDias(segunda, 6) }
}

/**
 * Lê o período da URL. Qualquer valor inválido cai no padrão (esta
 * semana), em vez de dar erro: o usuário sempre vê alguma coisa.
 */
export function daUrl(parametros: Record<string, string | string[] | undefined>, hoje: string): Periodo {
  const texto = (chave: string) => {
    const v = parametros[chave]
    return Array.isArray(v) ? v[0] : v
  }
  let tipo = texto('periodo') ?? PADRAO
  if (tipo === 'livre') {
    let de = lerDia(texto('de'))
    let ate = lerDia(texto('ate'))
    if (de && ate) {
      if (de > ate) [de, ate] = [ate, de]
      const limite = somarDias(de, MAXIMO_DIAS - 1)
      return { tipo: 'livre', inicio: de, fim: ate > limite ? limite : ate }
    }
    tipo = PADRAO
  }
  const valido = tipo === 'dia' || tipo === 'semana' || tipo === 'mes' ? tipo : 'semana'
  return doTipo(valido, lerDia(texto('data')) ?? hoje)
}

export const quantidadeDeDias = (p: Periodo) => diferencaEmDias(p.inicio, p.fim) + 1

/** O período vizinho: sentido -1 é o anterior, +1 o seguinte. */
export function deslocar(p: Periodo, sentido: -1 | 1): Periodo {
  if (p.tipo === 'mes') return doTipo('mes', sentido < 0 ? mesAnterior(p.inicio) : somarDias(p.fim, 1))
  const passo = quantidadeDeDias(p) * sentido
  return { tipo: p.tipo, inicio: somarDias(p.inicio, passo), fim: somarDias(p.fim, passo) }
}

export const contem = (p: Periodo, dia: string) => p.inicio <= dia && dia <= p.fim

/**
 * O período anterior, para a comparação "+12% que a semana passada".
 *
 * Se o período atual ainda está em andamento (contém hoje), o anterior é
 * cortado no mesmo ponto: quarta-feira desta semana é comparada com
 * segunda a quarta da semana passada, e não com a semana inteira, que
 * deixaria qualquer semana em andamento "no vermelho". Período que ainda
 * não começou não tem comparação.
 */
export function paraComparar(p: Periodo, hoje: string): Periodo | null {
  if (p.inicio > hoje) return null
  const anterior = deslocar(p, -1)
  if (contem(p, hoje)) {
    const corte = somarDias(anterior.inicio, diferencaEmDias(p.inicio, hoje))
    return { ...anterior, fim: corte < anterior.fim ? corte : anterior.fim }
  }
  return anterior
}

/** Parâmetros da URL que reproduzem este período. */
export function parametros(p: Periodo): Record<string, string> {
  if (p.tipo === 'livre') return { periodo: 'livre', de: p.inicio, ate: p.fim }
  return { periodo: p.tipo, data: p.inicio }
}

export const mesmoPeriodo = (a: Periodo, b: Periodo) => a.tipo === b.tipo && a.inicio === b.inicio && a.fim === b.fim

/** Diferença percentual, arredondada. null quando não há base de comparação. */
export function variacao(atual: number, anterior: number): number | null {
  if (!anterior) return null
  return Math.round(((atual - anterior) / anterior) * 100)
}

/** Dias do período que já aconteceram (a média por dia não conta dias futuros). */
export function diasDecorridos(p: Periodo, hoje: string): number {
  if (p.inicio > hoje) return 0
  return diferencaEmDias(p.inicio, p.fim < hoje ? p.fim : hoje) + 1
}
