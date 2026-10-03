/**
 * Balanço de atendimentos: o escopo (de quem é o balanço), o gráfico e a
 * lista. As contagens vêm do banco (função balanco_numeros); aqui só a
 * montagem do que a tela mostra. Mesma regra da versão Django (removida; está no histórico do git).
 */
import 'server-only'
import { horaLocal, somarDias } from './datas'
import { doTipo, primeiroDoMes, quantidadeDeDias, type Periodo, ultimoDoMes } from './periodo'
import type { SessaoDaBarbearia } from './sessao'

// Quantos atendimentos a lista da tela mostra. Os números do topo sempre
// consideram o período inteiro; para ver tudo, há o CSV.
export const MAXIMO_NA_LISTA = 500
// Até este número de dias o gráfico tem uma barra por dia; acima disso,
// uma barra por mês.
const MAXIMO_BARRAS_DIARIAS = 35

export interface Numeros {
  barbeiro_id: number | null
  quantidade: number
  clientes: number
  faltas: number
  cancelados: number
  por_dia: Record<string, number>
  por_mes: Record<string, number>
  por_barbeiro: { barbeiro_id: number | null; nome: string | null; quantidade: number }[]
}

export interface Barra {
  data: string
  periodo: Periodo
  quantidade: number
  futuro: boolean
  hoje: boolean
  rotulo: boolean
  altura: number
}

/**
 * Barras do gráfico: atendimentos por dia do período, incluindo os dias
 * sem atendimento (barra vazia), ou por mês em faixas longas. A altura é
 * proporcional ao dia mais movimentado. Dias futuros ficam sem barra.
 * Período de um dia só não tem gráfico: a lista já diz tudo.
 */
export function grafico(periodo: Periodo, numeros: Numeros, hoje: string) {
  const dias = quantidadeDeDias(periodo)
  if (dias === 1) return null
  const barras: Omit<Barra, 'altura'>[] = []
  let tipo: 'dia' | 'mes'
  if (dias <= MAXIMO_BARRAS_DIARIAS) {
    tipo = 'dia'
    for (let n = 0; n < dias; n++) {
      const dia = somarDias(periodo.inicio, n)
      barras.push({
        data: dia,
        periodo: doTipo('dia', dia),
        quantidade: numeros.por_dia[dia] ?? 0,
        futuro: dia > hoje,
        hoje: dia === hoje,
        // Num mês, rótulo só a cada 7 dias, para os números não se atropelarem no celular.
        rotulo: dias <= 14 || n % 7 === 0,
      })
    }
  } else {
    tipo = 'mes'
    for (let mes = primeiroDoMes(periodo.inicio); mes <= periodo.fim; mes = somarDias(ultimoDoMes(mes), 1)) {
      barras.push({
        data: mes,
        periodo: doTipo('mes', mes),
        quantidade: numeros.por_mes[mes.slice(0, 7)] ?? 0,
        futuro: mes > hoje,
        hoje: mes === primeiroDoMes(hoje),
        rotulo: true,
      })
    }
  }
  const maior = Math.max(0, ...barras.map((b) => b.quantidade))
  return {
    tipo,
    maior,
    barras: barras.map((b) => ({ ...b, altura: maior ? Math.round((b.quantidade / maior) * 100) : 0 })),
  }
}

/**
 * De quem é o balanço que a tela mostra. O barbeiro sempre vê o próprio:
 * o ?barbeiro= da URL é ignorado para ele (e a função do banco faz o
 * mesmo). O dono vê todos juntos ou escolhe um barbeiro.
 */
export async function escopoDoBalanco(sessao: SessaoDaBarbearia, pedido: string | undefined) {
  const { data } = await sessao.supabase.from('barbeiros').select('id, nome, ativo').order('nome')
  const todos = data ?? []
  if (sessao.ehBarbeiro) {
    const proprio = todos.find((b) => b.id === sessao.meuBarbeiro?.id) ?? null
    return { ehBarbeiro: true, barbeiro: proprio, permitidos: proprio ? [proprio] : [], semVinculo: !proprio }
  }
  const barbeiro = todos.find((b) => String(b.id) === pedido) ?? null
  return { ehBarbeiro: false, barbeiro, permitidos: todos, semVinculo: false }
}

export interface LinhaDaLista {
  id: number
  data: string
  observacoes: string
  criado_em: string
  cliente: { id: number; nome: string }
  barbeiro: { nome: string } | null
  agendamento: { inicio: string } | null
}

/**
 * Os atendimentos do período, do mais recente para o mais antigo. No mesmo
 * dia, os agendados vêm em ordem de horário e os avulsos (sem horário)
 * depois, na ordem em que foram registrados.
 */
export async function listaDoPeriodo(sessao: SessaoDaBarbearia, periodo: Periodo, barbeiroId: number | null, limite: number) {
  // A API do Supabase devolve no máximo 1000 linhas por consulta; para o
  // CSV de um período longo, buscamos em páginas.
  const PAGINA = 1000
  const lista: LinhaDaLista[] = []
  while (lista.length < limite) {
    let consulta = sessao.supabase
      .from('atendimentos')
      .select('id, data, observacoes, criado_em, cliente:clientes(id, nome), barbeiro:barbeiros(nome), agendamento:agendamentos(inicio)')
      .gte('data', periodo.inicio)
      .lte('data', periodo.fim)
      .order('data', { ascending: false })
      .order('criado_em')
      .order('id')
      .range(lista.length, Math.min(lista.length + PAGINA, limite) - 1)
    if (barbeiroId !== null) consulta = consulta.eq('barbeiro_id', barbeiroId)
    const pagina = ((await consulta).data ?? []) as unknown as LinhaDaLista[]
    lista.push(...pagina)
    if (pagina.length < PAGINA) break
  }
  const chave = (l: LinhaDaLista) => (l.agendamento ? horaLocal(l.agendamento.inicio) : '99:99')
  return lista.sort((a, b) => b.data.localeCompare(a.data) || chave(a).localeCompare(chave(b)))
}
