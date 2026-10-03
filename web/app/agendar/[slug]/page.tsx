import type { Metadata } from 'next'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import { diaEMes, diaLocal, horaLocal, lerDia, maiuscula, mesCurto, nomeCurtoDoDia, nomeDoDia } from '@/lib/datas'
import { clienteDoUsuario } from '@/lib/supabase/servidor'
import { FormConfirmar } from './FormConfirmar'
import { CabecalhoPublico } from '@/components/CabecalhoPublico'

interface ServicoPublico {
  id: number
  nome: string
  preco: number
  duracao_minutos: number
}
interface AgendaPublica {
  barbearia: { nome: string; slug: string; telefone: string; endereco: string }
  servicos: ServicoPublico[]
  cartoes?: { id: number; nome: string; proximo: string | null; hoje: boolean; situacao: string }[]
  barbeiro?: { id: number; nome: string }
  servico?: ServicoPublico
  dias?: string[]
  dia?: string | null
  horarios?: string[]
}

const reais = (valor: number) => `R$ ${Number(valor).toFixed(2).replace('.', ',')}`
const numero = (v: unknown) => (typeof v === 'string' && /^\d+$/.test(v) ? Number(v) : null)

export async function generateMetadata({ params }: PageProps<'/agendar/[slug]'>): Promise<Metadata> {
  const { slug } = await params
  const { data } = await (await clienteDoUsuario()).rpc('barbearia_publica', { p_slug: slug })
  return { title: { absolute: `Agendar · ${data?.nome ?? 'Martinho'}` }, manifest: `/agendar/${slug}/manifest.webmanifest` }
}

/**
 * Página de agendamento do cliente, sem login.
 * Fluxo: barbeiro -> serviço -> dia e horário -> nome e WhatsApp.
 * Cada escolha vai para a URL (?barbeiro=3&servico=1&data=...&hora=...),
 * então o link /agendar/<barbearia>?barbeiro=3 já abre com o barbeiro
 * escolhido, para cada um divulgar o seu.
 *
 * O visitante não lê nenhuma tabela: a página chama só a função pública
 * agenda_publica, que devolve os horários livres e mais nada.
 */
export default async function Agendar({ params, searchParams }: PageProps<'/agendar/[slug]'>) {
  const { slug } = await params
  const sp = await searchParams
  const supabase = await clienteDoUsuario()
  const { data } = await supabase.rpc('agenda_publica', {
    p_slug: slug,
    p_barbeiro: numero(sp.barbeiro),
    p_servico: numero(sp.servico),
    p_dia: lerDia(sp.data),
  })
  if (!data) notFound()
  const e = data as AgendaPublica
  const base = `/agendar/${slug}`
  // O horário só vale para o dia que o cliente escolheu: se aquele dia
  // não está mais disponível, o horário é descartado, para nunca agendar
  // num dia diferente do que o cliente viu.
  const inicio = e.dia && e.dia === sp.data ? (e.horarios ?? []).find((h) => horaLocal(h) === sp.hora) : undefined
  const comBarbeiro = (extra: Record<string, string | number> = {}) =>
    `${base}?${new URLSearchParams({ barbeiro: String(e.barbeiro?.id ?? ''), ...Object.fromEntries(Object.entries(extra).map(([k, val]) => [k, String(val)])) })}`

  return (
    <>
      <CabecalhoPublico barbearia={e.barbearia} />
      <main className="publico__conteudo publico__principal">
        {/* Passo 1: barbeiro */}
        <section className="passo" id="passo-barbeiro">
          <div className="passo__titulo">
            <span className="passo__numero">1</span>
            <h2 className="subtitulo">Barbeiro</h2>
            {e.barbeiro && (
              <Link className="passo__trocar" href={`${base}#passo-barbeiro`}>
                Trocar
              </Link>
            )}
          </div>
          {e.barbeiro ? (
            <p className="passo__escolha">{e.barbeiro.nome}</p>
          ) : e.cartoes?.length ? (
            <ul className="opcoes">
              {e.cartoes.map((c) => {
                const miolo = (
                  <>
                    <span className="opcao__inicial" aria-hidden="true">
                      {c.nome.charAt(0)}
                    </span>
                    <span className="opcao__textos">
                      <span className="opcao__nome">{c.nome}</span>
                      <span className={`opcao__situacao opcao__situacao--${c.hoje ? 'hoje' : c.proximo ? 'depois' : 'sem'}`}>
                        {c.proximo
                          ? c.hoje
                            ? `Atendendo hoje · próximo horário ${horaLocal(c.proximo)}`
                            : `${c.situacao} · próximo horário ${nomeCurtoDoDia(diaLocal(c.proximo))}, ${diaLocal(c.proximo).slice(8)}/${diaLocal(c.proximo).slice(5, 7)} às ${horaLocal(c.proximo)}`
                          : 'Sem horários livres nos próximos dias'}
                      </span>
                    </span>
                  </>
                )
                return (
                  <li key={c.id}>
                    {c.proximo ? (
                      <Link className="opcao opcao--barbeiro" href={`${base}?barbeiro=${c.id}#passo-servico`}>
                        {miolo}
                      </Link>
                    ) : (
                      <div className="opcao opcao--barbeiro opcao--indisponivel" aria-disabled="true">
                        {miolo}
                      </div>
                    )}
                  </li>
                )
              })}
            </ul>
          ) : (
            <p className="legenda">A barbearia ainda não cadastrou os horários dos barbeiros.</p>
          )}
        </section>

        {/* Passo 2: serviço */}
        {e.barbeiro && (
          <section className="passo" id="passo-servico">
            <div className="passo__titulo">
              <span className="passo__numero">2</span>
              <h2 className="subtitulo">Serviço</h2>
              {e.servico && (
                <Link className="passo__trocar" href={`${comBarbeiro()}#passo-servico`}>
                  Trocar
                </Link>
              )}
            </div>
            {e.servico ? (
              <p className="passo__escolha">
                {e.servico.nome} · {e.servico.duracao_minutos} min · {reais(e.servico.preco)}
              </p>
            ) : e.servicos.length ? (
              <ul className="opcoes">
                {e.servicos.map((s) => (
                  <li key={s.id}>
                    <Link className="opcao" href={`${comBarbeiro({ servico: s.id })}#passo-agenda`}>
                      <span className="opcao__nome">{s.nome}</span>
                      <span className="opcao__detalhe">{s.duracao_minutos} min</span>
                      <span className="opcao__preco">{reais(s.preco)}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="legenda">A barbearia ainda não cadastrou serviços para agendamento online.</p>
            )}
          </section>
        )}

        {/* Passo 3: agenda do barbeiro */}
        {e.barbeiro && e.servico && (
          <section className="passo" id="passo-agenda">
            <div className="passo__titulo">
              <span className="passo__numero">3</span>
              <h2 className="subtitulo">Agenda de {e.barbeiro.nome}</h2>
            </div>
            {e.dias?.length && e.dia ? (
              <>
                <div className="dias" role="list">
                  {e.dias.map((d) => (
                    <Link
                      key={d}
                      role="listitem"
                      className={`dia${d === e.dia ? ' dia--ativo' : ''}`}
                      href={`${comBarbeiro({ servico: e.servico!.id, data: d })}#passo-agenda`}
                      aria-current={d === e.dia ? 'date' : undefined}
                    >
                      <span className="dia__semana">{nomeCurtoDoDia(d)}</span>
                      <span className="dia__numero">{d.slice(8)}</span>
                      <span className="dia__mes">{mesCurto(d)}</span>
                    </Link>
                  ))}
                </div>
                <p className="legenda">
                  Horários livres {nomeDoDia(e.dia)}, {diaEMes(e.dia)}. Toque para escolher.
                </p>
                <div className="horarios">
                  {(e.horarios ?? []).map((h) => (
                    <Link
                      key={h}
                      className={`horario${h === inicio ? ' horario--ativo' : ''}`}
                      href={`${comBarbeiro({ servico: e.servico!.id, data: e.dia!, hora: horaLocal(h) })}#passo-dados`}
                    >
                      {horaLocal(h)}
                    </Link>
                  ))}
                </div>
              </>
            ) : (
              <p className="legenda">
                {e.barbeiro.nome} não tem horários livres nos próximos dias. <Link href={`${base}#passo-barbeiro`}>Escolha outro barbeiro</Link>.
              </p>
            )}
          </section>
        )}

        {/* Passo 4: dados do cliente */}
        {e.barbeiro && e.servico && inicio && (
          <section className="passo" id="passo-dados">
            <div className="passo__titulo">
              <span className="passo__numero">4</span>
              <h2 className="subtitulo">Seus dados</h2>
            </div>
            <div className="resumo">
              <p>
                <strong>{e.servico.nome}</strong> com {e.barbeiro.nome}
              </p>
              <p>
                {maiuscula(nomeDoDia(diaLocal(inicio)))}, {diaEMes(diaLocal(inicio))} às <strong>{horaLocal(inicio)}</strong>
              </p>
            </div>
            <FormConfirmar slug={slug} barbeiro={e.barbeiro.id} servico={e.servico.id} inicio={inicio} />
          </section>
        )}

        {e.barbearia.telefone && <p className="legenda publico__contato">Dúvidas? Fale com a barbearia: {e.barbearia.telefone}</p>}
      </main>
    </>
  )
}
