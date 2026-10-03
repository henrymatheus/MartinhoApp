import type { Metadata } from 'next'
import Link from 'next/link'
import { Seta } from '@/components/Campo'
import { Pagina, Vazio } from '@/components/Pagina'
import { aniversarioEm, ausenteEm, mensagemAusencia, mensagemLembrete, situacaoNoDia } from '@/lib/agenda'
import { diaEMes, diaLocal, ddmm, hojeLocal, horaLocal, instante, lerDia, maiuscula, nomeCurtoDoDia, nomeDoDia, somarDias } from '@/lib/datas'
import { exigirBarbearia, podeEditarBarbeiro } from '@/lib/sessao'
import { linkWhatsapp } from '@/lib/telefones'
import { NOMES_STATUS, type Ausencia, type HorarioTrabalho, type Status } from '@/lib/tipos'
import { desfazerAusencia, marcarAusencia, mudarStatus } from './acoes'

export const metadata: Metadata = { title: 'Agenda' }

interface AgendamentoDoDia {
  id: number
  inicio: string
  fim: string
  status: Status
  observacoes: string
  cliente: { id: number; nome: string; telefone: string; data_nascimento: string | null }
  barbeiro: { id: number; nome: string }
  servico: { nome: string; duracao_minutos: number }
}

const IconeWhatsapp = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z" />
  </svg>
)

/** A agenda de um dia (hoje, se nenhum for escolhido), em ordem de horário. */
export default async function Agenda({ searchParams }: PageProps<'/'>) {
  const sessao = await exigirBarbearia()
  const { supabase, barbearia } = sessao
  const dia = lerDia((await searchParams).data) ?? hojeLocal()
  const hoje = hojeLocal()
  const ehHoje = dia === hoje
  const agora = new Date()

  // Sem filtro de barbearia nas consultas: a RLS do banco já devolve só
  // as linhas da barbearia do usuário.
  const [rAgendamentos, rBarbeiros, rAusencias] = await Promise.all([
    supabase
      .from('agendamentos')
      .select('id, inicio, fim, status, observacoes, cliente:clientes(id, nome, telefone, data_nascimento), barbeiro:barbeiros(id, nome), servico:servicos(nome, duracao_minutos)')
      .gte('inicio', instante(dia, '00:00').toISOString())
      .lt('inicio', instante(somarDias(dia, 1), '00:00').toISOString())
      .order('inicio'),
    supabase.from('barbeiros').select('id, nome, horarios:horarios_trabalho(id, barbeiro_id, dia_semana, inicio, fim)').eq('ativo', true).order('nome'),
    supabase.from('ausencias').select('*').lte('data_inicio', dia).gte('data_fim', dia),
  ])
  const agendamentos = (rAgendamentos.data ?? []) as unknown as AgendamentoDoDia[]
  const ausencias = (rAusencias.data ?? []) as Ausencia[]
  const barbeiros = (rBarbeiros.data ?? []) as unknown as { id: number; nome: string; horarios: HorarioTrabalho[] }[]

  const equipe = barbeiros.map((b) => ({
    barbeiro: b,
    podeEditar: podeEditarBarbeiro(sessao, b.id),
    ...situacaoNoDia(b.horarios, ausencias.filter((a) => a.barbeiro_id === b.id), dia),
  }))

  const cartoes = agendamentos.map((ag) => {
    const dados = { barbearia: barbearia.nome, cliente: ag.cliente.nome, barbeiro: ag.barbeiro.nome, servico: ag.servico.nome, inicio: ag.inicio }
    // Horário marcado com um barbeiro que ficou ausente: destacado, com a
    // mensagem pronta para avisar o cliente. Nada é cancelado sozinho.
    const barbeiroAusente = ag.status === 'agendado' && ausenteEm(ausencias, ag.barbeiro.id, new Date(ag.inicio), new Date(ag.fim))
    return {
      ...ag,
      aniversariante: aniversarioEm(ag.cliente.data_nascimento, dia),
      barbeiroAusente,
      whatsapp: linkWhatsapp(ag.cliente.telefone, barbeiroAusente ? mensagemAusencia(dados) : mensagemLembrete(dados)),
    }
  })
  const totalAtivos = cartoes.filter((ag) => ag.status === 'agendado').length

  // A linha dourada "agora" vai antes do primeiro horário que ainda não terminou.
  const agoraAntesDe = ehHoje ? (cartoes.find((ag) => new Date(ag.fim) > agora)?.id ?? 'fim') : null
  const linhaAgora = <li className="agora">Agora · {horaLocal(agora)}</li>

  // Dia vazio: os próximos horários marcados, para ninguém achar que um
  // agendamento sumiu só porque está em outro dia.
  const proximos = agendamentos.length
    ? []
    : (((
        await supabase
          .from('agendamentos')
          .select('id, inicio, cliente:clientes(nome), barbeiro:barbeiros(nome), servico:servicos(nome)')
          .eq('status', 'agendado')
          .gte('inicio', agora.toISOString())
          .order('inicio')
          .limit(5)
      ).data ?? []) as unknown as { id: number; inicio: string; cliente: { nome: string }; barbeiro: { nome: string }; servico: { nome: string } }[])

  return (
    <Pagina>
      <div className="cabecalho">
        <div className="cabecalho__textos">
          <span className="rotulo">{ehHoje ? 'Hoje' : 'Agenda'}</span>
          <h1 className="titulo">
            {maiuscula(nomeDoDia(dia))}, {diaEMes(dia)}
          </h1>
          <p className="legenda">
            {agendamentos.length
              ? `${agendamentos.length} horário${agendamentos.length === 1 ? '' : 's'}${totalAtivos ? `, ${totalAtivos} a atender` : ''}`
              : 'Nenhum horário marcado'}
          </p>
        </div>
        <div className="linha-acoes">
          <nav className="navegacao-dia" aria-label="Trocar de dia">
            <Link className="btn btn--secundario btn--icone" href={`/?data=${somarDias(dia, -1)}`} aria-label="Dia anterior">
              <Seta.Esquerda />
            </Link>
            {!ehHoje && (
              <Link className="btn btn--secundario" href={`/?data=${hoje}`}>
                Hoje
              </Link>
            )}
            <Link className="btn btn--secundario btn--icone" href={`/?data=${somarDias(dia, 1)}`} aria-label="Próximo dia">
              <Seta.Direita />
            </Link>
          </nav>
          <Link className="btn btn--secundario" href="/atendimentos/novo">
            Sem hora marcada
          </Link>
          <Link className="btn btn--primario" href={`/agendamentos/novo?data=${dia}`}>
            Novo agendamento
          </Link>
        </div>
      </div>

      {equipe.length > 0 && (
        <section className="equipe" aria-label="Equipe do dia">
          <h2 className="rotulo">Equipe {ehHoje ? 'hoje' : 'neste dia'}</h2>
          <ul className="equipe__lista">
            {equipe.map((m) => (
              <li key={m.barbeiro.id} className={`equipe__membro equipe__membro--${m.situacao}`}>
                <span className="equipe__ponto" aria-hidden="true" />
                <div className="equipe__textos">
                  <span className="corpo-forte">{m.barbeiro.nome}</span>
                  <span className="legenda">{m.texto}</span>
                </div>
                {m.podeEditar && dia >= hoje && (
                  <div className="equipe__acoes">
                    {m.desfazer.map((a) => (
                      <form key={a.id} action={desfazerAusencia.bind(null, a.id)}>
                        <button className="btn btn--texto btn--pequeno" type="submit">
                          Desfazer ausência
                        </button>
                      </form>
                    ))}
                    {(m.situacao === 'atendendo' || m.situacao === 'parcial') && (
                      <>
                        {ehHoje && (
                          <form action={marcarAusencia.bind(null, m.barbeiro.id, dia, 'agora')}>
                            <button className="btn btn--texto btn--pequeno" type="submit">
                              Saiu agora
                            </button>
                          </form>
                        )}
                        <form action={marcarAusencia.bind(null, m.barbeiro.id, dia, 'dia')}>
                          <button className="btn btn--secundario btn--pequeno" type="submit">
                            {ehHoje ? 'Faltou hoje' : 'Ausente neste dia'}
                          </button>
                        </form>
                      </>
                    )}
                  </div>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      {cartoes.length ? (
        <ol className="lista-agenda">
          {cartoes.map((ag) => (
            <FragmentoAgendamento key={ag.id} antes={agoraAntesDe === ag.id ? linhaAgora : null}>
              <li
                className={`agendamento${ag.status !== 'agendado' ? ' agendamento--encerrado' : ''}${ag.barbeiroAusente ? ' agendamento--alerta' : ''}`}
              >
                <div className="agendamento__hora">{horaLocal(ag.inicio)}</div>
                <div className="agendamento__cliente">
                  <Link href={`/clientes/${ag.cliente.id}`}>{ag.cliente.nome}</Link>
                  {ag.aniversariante && <span className="aniversario">Aniversário hoje</span>}
                </div>
                <span className={`status status--${ag.status}`}>{NOMES_STATUS[ag.status]}</span>
                <div className="agendamento__meta">
                  {ag.servico.nome} · {ag.servico.duracao_minutos} min · com {ag.barbeiro.nome}
                  {ag.observacoes && ` · ${ag.observacoes}`}
                </div>
                {ag.barbeiroAusente && (
                  <p className="agendamento__alerta">{ag.barbeiro.nome} está ausente neste horário. Remarque ou avise o cliente.</p>
                )}
                {ag.status === 'agendado' && (
                  <div className="agendamento__acoes">
                    <form action={mudarStatus.bind(null, ag.id, 'concluir')}>
                      <button className="btn btn--primario btn--pequeno" type="submit">
                        Concluir atendimento
                      </button>
                    </form>
                    {ag.whatsapp && (
                      <a className="btn btn--secundario btn--pequeno" href={ag.whatsapp} target="_blank" rel="noopener">
                        {ag.barbeiroAusente ? (
                          'Avisar cliente no WhatsApp'
                        ) : (
                          <>
                            <IconeWhatsapp /> Lembrar no WhatsApp
                          </>
                        )}
                      </a>
                    )}
                    <Link className="btn btn--texto btn--pequeno" href={`/agendamentos/${ag.id}/editar`}>
                      Remarcar
                    </Link>
                    <form action={mudarStatus.bind(null, ag.id, 'faltou')}>
                      <button className="btn btn--texto btn--pequeno" type="submit">
                        Faltou
                      </button>
                    </form>
                    <form action={mudarStatus.bind(null, ag.id, 'cancelar')}>
                      <button className="btn btn--texto btn--pequeno" type="submit">
                        Cancelar
                      </button>
                    </form>
                  </div>
                )}
              </li>
            </FragmentoAgendamento>
          ))}
          {agoraAntesDe === 'fim' && linhaAgora}
        </ol>
      ) : (
        <>
          <Vazio titulo={`Nenhum horário marcado ${ehHoje ? 'hoje' : 'neste dia'}`}>
            <p>Os agendamentos aparecem aqui em ordem de horário.</p>
            <Link className="btn btn--primario" href={`/agendamentos/novo?data=${dia}`}>
              Novo agendamento
            </Link>
          </Vazio>
          {proximos.length > 0 && (
            <section className="formulario">
              <h2 className="subtitulo">Próximos horários marcados</h2>
              <div className="tabela-rolagem">
                <table className="tabela">
                  <thead>
                    <tr>
                      <th>Quando</th>
                      <th>Cliente</th>
                      <th>Serviço</th>
                      <th>Barbeiro</th>
                    </tr>
                  </thead>
                  <tbody>
                    {proximos.map((ag) => (
                      <tr key={ag.id}>
                        <td>
                          <Link href={`/?data=${diaLocal(ag.inicio)}`}>
                            {maiuscula(nomeCurtoDoDia(diaLocal(ag.inicio)))}, {ddmm(diaLocal(ag.inicio))} · {horaLocal(ag.inicio)}
                          </Link>
                        </td>
                        <td>{ag.cliente.nome}</td>
                        <td>{ag.servico.nome}</td>
                        <td>{ag.barbeiro.nome}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
        </>
      )}
    </Pagina>
  )
}

function FragmentoAgendamento({ antes, children }: { antes: React.ReactNode; children: React.ReactNode }) {
  return (
    <>
      {antes}
      {children}
    </>
  )
}
