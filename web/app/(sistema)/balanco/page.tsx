import type { Metadata } from 'next'
import Link from 'next/link'
import { Seta } from '@/components/Campo'
import { Pagina, Vazio } from '@/components/Pagina'
import { escopoDoBalanco, grafico, listaDoPeriodo, MAXIMO_NA_LISTA, type Numeros } from '@/lib/balanco'
import { ddmm, ddmmaaaa, diaEMes, hojeLocal, horaLocal, maiuscula, mesCurto, nomeCurtoDoDia, nomeDoDia, nomeDoMes } from '@/lib/datas'
import {
  contem,
  daUrl,
  deslocar,
  doTipo,
  diasDecorridos,
  mesAnterior,
  mesmoPeriodo,
  paraComparar,
  parametros,
  type Periodo,
  quantidadeDeDias,
  variacao,
} from '@/lib/periodo'
import { exigirBarbearia } from '@/lib/sessao'
import { FiltroBarbeiro } from './FiltroBarbeiro'

export const metadata: Metadata = { title: 'Balanço' }

/**
 * Painel de atendimentos do período: quantidade, gráfico por dia,
 * comparação com o período anterior, estatísticas, resumo por barbeiro
 * (para o dono) e a lista dia a dia. Sem valores em dinheiro por enquanto.
 */
export default async function Balanco({ searchParams }: PageProps<'/balanco'>) {
  const sessao = await exigirBarbearia()
  const sp = await searchParams
  const hoje = hojeLocal()
  const periodo = daUrl(sp, hoje)
  const escopo = await escopoDoBalanco(sessao, typeof sp.barbeiro === 'string' ? sp.barbeiro : undefined)
  const barbeiroId = escopo.barbeiro?.id ?? null

  const urlCom = (caminho: string, p: Periodo, barbeiro: number | null = barbeiroId) => {
    const ps = new URLSearchParams(parametros(p))
    if (barbeiro !== null && !escopo.ehBarbeiro) ps.set('barbeiro', String(barbeiro))
    return `${caminho}?${ps}`
  }
  const atalhos = [
    { texto: 'Hoje', p: doTipo('dia', hoje) },
    { texto: 'Esta semana', p: doTipo('semana', hoje) },
    { texto: 'Este mês', p: doTipo('mes', hoje) },
    { texto: 'Mês passado', p: doTipo('mes', mesAnterior(hoje)) },
  ]

  let conteudo: React.ReactNode
  if (escopo.semVinculo) {
    conteudo = (
      <Vazio titulo="Seu login ainda não está ligado a um barbeiro">
        <p>Peça ao dono da barbearia para ligar o seu usuário à sua ficha de barbeiro. Depois disso, seu balanço aparece aqui.</p>
      </Vazio>
    )
  } else {
    const anterior = paraComparar(periodo, hoje)
    const numerosDe = async (p: Periodo) =>
      (await sessao.supabase.rpc('balanco_numeros', { p_inicio: p.inicio, p_fim: p.fim, p_barbeiro: barbeiroId })).data as Numeros | null
    const [numeros, numerosAnteriores, lista] = await Promise.all([
      numerosDe(periodo),
      anterior ? numerosDe(anterior) : null,
      listaDoPeriodo(sessao, periodo, barbeiroId, MAXIMO_NA_LISTA),
    ])
    conteudo = numeros ? (
      <Painel
        periodo={periodo}
        hoje={hoje}
        numeros={numeros}
        comparacao={anterior && numerosAnteriores ? { quantidade: numerosAnteriores.quantidade, variacao: variacao(numeros.quantidade, numerosAnteriores.quantidade) } : null}
        lista={lista}
        mostrarBarbeiro={barbeiroId === null}
        urlCom={urlCom}
      />
    ) : null
  }

  return (
    <Pagina>
      <div className="cabecalho">
        <div className="cabecalho__textos">
          <span className="rotulo">{escopo.ehBarbeiro ? (escopo.barbeiro?.nome ?? '') : (escopo.barbeiro?.nome ?? 'Todos os barbeiros')}</span>
          <h1 className="titulo">{escopo.ehBarbeiro ? 'Meu balanço' : 'Balanço'}</h1>
        </div>
        {!escopo.semVinculo && (
          <Link className="btn btn--primario" href="/atendimentos/novo">
            Registrar atendimento
          </Link>
        )}
      </div>

      <div className="filtros">
        <div className="atalhos">
          <nav className="atalhos__lista" aria-label="Períodos">
            {atalhos.map((a) => (
              <Link key={a.texto} className="atalho" href={urlCom('/balanco', a.p)} aria-current={mesmoPeriodo(a.p, periodo) ? 'page' : undefined}>
                {a.texto}
              </Link>
            ))}
          </nav>
          <details className="personalizado" open={periodo.tipo === 'livre'}>
            <summary className="atalho" aria-current={periodo.tipo === 'livre' ? 'page' : undefined}>
              Escolher datas
            </summary>
            <form className="personalizado__form" method="get">
              <input type="hidden" name="periodo" value="livre" />
              {barbeiroId !== null && !escopo.ehBarbeiro && <input type="hidden" name="barbeiro" value={barbeiroId} />}
              <div className="campo">
                <label htmlFor="de">De</label>
                <input id="de" type="date" name="de" defaultValue={periodo.inicio} required />
              </div>
              <div className="campo">
                <label htmlFor="ate">Até</label>
                <input id="ate" type="date" name="ate" defaultValue={periodo.fim} required />
              </div>
              <button className="btn btn--secundario" type="submit">
                Ver
              </button>
            </form>
          </details>
        </div>
        {!escopo.ehBarbeiro && (
          <FiltroBarbeiro parametros={parametros(periodo)} barbeiros={escopo.permitidos} atual={barbeiroId} />
        )}
      </div>

      {conteudo}
    </Pagina>
  )
}

function textoDoPeriodo(p: Periodo, hoje: string) {
  if (p.tipo === 'dia') return p.inicio === hoje ? 'Hoje' : `${maiuscula(nomeDoDia(p.inicio))}, ${diaEMes(p.inicio)}`
  if (p.tipo === 'semana') return contem(p, hoje) ? 'Esta semana' : `Semana de ${ddmm(p.inicio)}`
  if (p.tipo === 'mes') return `${maiuscula(nomeDoMes(p.inicio))} de ${p.inicio.slice(0, 4)}`
  return `${quantidadeDeDias(p)} dias`
}

function Painel({
  periodo,
  hoje,
  numeros,
  comparacao,
  lista,
  mostrarBarbeiro,
  urlCom,
}: {
  periodo: Periodo
  hoje: string
  numeros: Numeros
  comparacao: { quantidade: number; variacao: number | null } | null
  lista: Awaited<ReturnType<typeof listaDoPeriodo>>
  mostrarBarbeiro: boolean
  urlCom: (caminho: string, p: Periodo, barbeiro?: number | null) => string
}) {
  const g = grafico(periodo, numeros, hoje)
  const decorridos = diasDecorridos(periodo, hoje)
  // Uma casa decimal: 3,4 atendimentos por dia diz mais que "3".
  const media = decorridos ? (Math.round((numeros.quantidade / decorridos) * 10) / 10).toLocaleString('pt-BR') : '0'
  const q = numeros.quantidade
  const plural = (n: number) => (n === 1 ? '' : 's')
  const nomeAnterior = { dia: 'que o dia anterior', semana: 'que a semana anterior', mes: 'que o mês anterior', livre: 'que o período anterior' }[periodo.tipo]

  // Agrupa a lista por dia, com a quantidade de cada dia.
  const dias: { data: string; itens: typeof lista }[] = []
  for (const at of lista) {
    if (dias.at(-1)?.data !== at.data) dias.push({ data: at.data, itens: [] })
    dias.at(-1)!.itens.push(at)
  }

  return (
    <>
      <section className="cartao painel" aria-label="Atendimentos do período">
        <div className="painel__periodo">
          <Link className="btn btn--texto btn--icone" href={urlCom('/balanco', deslocar(periodo, -1))} aria-label="Período anterior">
            <Seta.Esquerda />
          </Link>
          <div className="painel__datas">
            <span className="corpo-forte">{textoDoPeriodo(periodo, hoje)}</span>
            <span className="legenda">{periodo.tipo === 'dia' ? ddmmaaaa(periodo.inicio) : `${ddmm(periodo.inicio)} a ${ddmmaaaa(periodo.fim)}`}</span>
          </div>
          {/* Não há atendimento no futuro: a seta "próximo" para no período atual. */}
          {periodo.fim < hoje ? (
            <Link className="btn btn--texto btn--icone" href={urlCom('/balanco', deslocar(periodo, 1))} aria-label="Próximo período">
              <Seta.Direita />
            </Link>
          ) : (
            <span className="btn--icone" aria-hidden="true" />
          )}
        </div>

        <p className="painel__total">{q}</p>
        <p className="painel__unidade">atendimento{plural(q)}</p>
        {comparacao && comparacao.variacao !== null && (
          <p className={`variacao${comparacao.variacao > 0 ? ' variacao--alta' : comparacao.variacao < 0 ? ' variacao--baixa' : ''}`}>
            {comparacao.variacao > 0 ? `▲ +${comparacao.variacao}%` : comparacao.variacao < 0 ? `▼ ${comparacao.variacao}%` : '0%'}{' '}
            <span className="legenda">
              {nomeAnterior}
              {periodo.tipo !== 'dia' && contem(periodo, hoje) && ', até o mesmo dia'} ({comparacao.quantidade})
            </span>
          </p>
        )}

        {g && g.maior > 0 && (
          <figure className="grafico" aria-label={`Atendimentos por ${g.tipo === 'mes' ? 'mês' : 'dia'}`}>
            <div className="grafico__area" style={{ '--barras': g.barras.length } as React.CSSProperties}>
              <span className="grafico__maior">{g.maior}</span>
              {g.barras.map((b) =>
                b.futuro ? (
                  <span key={b.data} className="grafico__coluna" aria-hidden="true" />
                ) : (
                  <Link
                    key={b.data}
                    className="grafico__coluna"
                    href={urlCom('/balanco', b.periodo)}
                    aria-label={`${g.tipo === 'mes' ? `${nomeDoMes(b.data)}/${b.data.slice(0, 4)}` : `${nomeDoDia(b.data)}, ${ddmm(b.data)}`}: ${b.quantidade} atendimento${plural(b.quantidade)}`}
                  >
                    <span className="grafico__barra" style={{ height: `${b.altura}%` }} />
                    <span className="grafico__dica" aria-hidden="true">
                      <strong>{b.quantidade}</strong>
                      <span>{g.tipo === 'mes' ? `${maiuscula(mesCurto(b.data))}/${b.data.slice(0, 4)}` : `${maiuscula(nomeCurtoDoDia(b.data))}, ${ddmm(b.data)}`}</span>
                    </span>
                  </Link>
                ),
              )}
            </div>
            <div className="grafico__eixo" style={{ '--barras': g.barras.length } as React.CSSProperties} aria-hidden="true">
              {g.barras.map((b) => (
                <span key={b.data} className={b.hoje ? 'grafico__hoje' : undefined}>
                  {b.rotulo &&
                    (g.tipo === 'mes' ? (
                      maiuscula(mesCurto(b.data))
                    ) : (
                      <>
                        {Number(b.data.slice(8))}
                        {g.barras.length <= 7 && (
                          <>
                            <br />
                            {maiuscula(nomeCurtoDoDia(b.data))}
                          </>
                        )}
                      </>
                    ))}
                </span>
              ))}
            </div>
          </figure>
        )}
      </section>

      <section className="formulario">
        <h2 className="subtitulo">Estatísticas</h2>
        <dl className="cartao estatisticas">
          <div>
            <dt>Média por dia</dt>
            <dd>{media}</dd>
          </div>
          <div>
            <dt>Clientes atendidos</dt>
            <dd>{numeros.clientes}</dd>
          </div>
          <div>
            <dt>Faltas</dt>
            <dd>{numeros.faltas}</dd>
          </div>
          <div>
            <dt>Cancelamentos</dt>
            <dd>{numeros.cancelados}</dd>
          </div>
        </dl>
      </section>

      {q > 0 ? (
        <>
          {mostrarBarbeiro && numeros.por_barbeiro.length > 0 && (
            <section className="formulario">
              <h2 className="subtitulo">Por barbeiro</h2>
              <ul className="cartao detalhamento">
                {numeros.por_barbeiro.map((linha) => (
                  <li key={linha.barbeiro_id ?? 'sem'}>
                    {linha.barbeiro_id ? <Link href={urlCom('/balanco', periodo, linha.barbeiro_id)}>{linha.nome}</Link> : <span>Sem barbeiro</span>}
                    <span className="numero corpo-forte">{linha.quantidade}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section className="formulario">
            <div className="cabecalho">
              <h2 className="subtitulo">Atendimentos</h2>
              <a className="btn btn--texto btn--pequeno" href={urlCom('/balanco/exportar', periodo)}>
                Baixar planilha (CSV)
              </a>
            </div>
            {q > MAXIMO_NA_LISTA && (
              <p className="legenda">
                A lista mostra os {MAXIMO_NA_LISTA} atendimentos mais recentes. Baixe a planilha para ver todos os {q}.
              </p>
            )}
            {dias.map((dia) => (
              <div className="dia-balanco" key={dia.data}>
                <div className="dia-balanco__topo">
                  <h3 className="corpo-forte">{dia.data === hoje ? 'Hoje' : `${maiuscula(nomeDoDia(dia.data))}, ${ddmm(dia.data)}`}</h3>
                  <span className="legenda">
                    {numeros.por_dia[dia.data] ?? dia.itens.length} atendimento{plural(numeros.por_dia[dia.data] ?? dia.itens.length)}
                  </span>
                </div>
                <ul className="cartao linhas">
                  {dia.itens.map((at) => (
                    <li className="linha-atendimento" key={at.id}>
                      <span className="linha-atendimento__hora">
                        {at.agendamento ? horaLocal(at.agendamento.inicio) : <span className="etiqueta">avulso</span>}
                      </span>
                      <div className="linha-atendimento__textos">
                        <Link href={`/clientes/${at.cliente.id}`}>{at.cliente.nome}</Link>
                        {mostrarBarbeiro && <span className="legenda">com {at.barbeiro?.nome ?? '—'}</span>}
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </section>
        </>
      ) : (
        <Vazio titulo={`Nenhum atendimento neste período${contem(periodo, hoje) ? ' ainda' : ''}`}>
          <p>
            Os atendimentos entram aqui quando você toca em &quot;Concluir atendimento&quot; na agenda, ou quando registra alguém que chegou sem hora
            marcada.
          </p>
          <Link className="btn btn--primario" href="/atendimentos/novo">
            Registrar atendimento
          </Link>
        </Vazio>
      )}
    </>
  )
}
