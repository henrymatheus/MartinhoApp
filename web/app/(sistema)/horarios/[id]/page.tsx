import type { Metadata } from 'next'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import { Pagina } from '@/components/Pagina'
import { descreverAusencia, hhmm } from '@/lib/agenda'
import { hojeLocal, NOMES_DOS_DIAS } from '@/lib/datas'
import { exigirBarbearia, podeEditarBarbeiro } from '@/lib/sessao'
import type { Ausencia, HorarioTrabalho } from '@/lib/tipos'
import { removerAusencia } from '../acoes'
import { FormAusencia } from './FormAusencia'
import { FormSemana } from './FormSemana'

export const metadata: Metadata = { title: 'Horários do barbeiro' }

/** Turnos da semana e ausências de um barbeiro. */
export default async function HorariosDoBarbeiro({ params }: PageProps<'/horarios/[id]'>) {
  const sessao = await exigirBarbearia()
  const id = Number((await params).id)
  const { data: barbeiro } = Number.isInteger(id)
    ? await sessao.supabase.from('barbeiros').select('id, nome').eq('id', id).eq('ativo', true).maybeSingle()
    : { data: null }
  if (!barbeiro) notFound()
  const pode = podeEditarBarbeiro(sessao, id)

  const [{ data: horarios }, { data: ausencias }] = await Promise.all([
    sessao.supabase.from('horarios_trabalho').select('*').eq('barbeiro_id', id).order('dia_semana').order('inicio'),
    sessao.supabase.from('ausencias').select('*').eq('barbeiro_id', id).gte('data_fim', hojeLocal()).order('data_inicio').order('hora_inicio'),
  ])

  // Valores iniciais do formulário da semana, com os mesmos nomes de campo.
  const inicial: Record<string, string> = {}
  for (const dia of NOMES_DOS_DIAS.keys()) {
    const turnos = ((horarios ?? []) as HorarioTrabalho[]).filter((h) => h.dia_semana === dia)
    if (turnos.length) inicial[`d${dia}_ativo`] = 'on'
    turnos.slice(0, 2).forEach((t, i) => {
      inicial[`d${dia}_inicio${i + 1}`] = hhmm(t.inicio)
      inicial[`d${dia}_fim${i + 1}`] = hhmm(t.fim)
    })
  }

  return (
    <Pagina>
      <div className="cabecalho">
        <div className="cabecalho__textos">
          {!sessao.ehBarbeiro && (
            <Link className="legenda" href="/horarios">
              Horários
            </Link>
          )}
          <h1 className="titulo">{barbeiro.nome}</h1>
          <p className="legenda">
            {pode
              ? 'Marque os dias em que atende. A tarde é opcional: o intervalo entre manhã e tarde é o almoço.'
              : 'Só o dono da barbearia ou o próprio barbeiro alteram estes horários.'}
          </p>
        </div>
      </div>

      {pode ? (
        <FormSemana barbeiroId={id} inicial={inicial} />
      ) : (
        <div className="cartao">
          {((horarios ?? []) as HorarioTrabalho[]).map((h) => (
            <div key={h.id}>
              {NOMES_DOS_DIAS[h.dia_semana]} {hhmm(h.inicio)}-{hhmm(h.fim)}
            </div>
          ))}
        </div>
      )}

      <section className="formulario">
        <h2 className="subtitulo">Folgas, férias e ausências</h2>
        <p className="legenda">
          Nesses períodos o barbeiro não aparece para os clientes. Com horário, vale só aquele trecho de um dia. Agendamentos já marcados não são
          cancelados: eles ficam destacados na agenda.
        </p>
        {!!ausencias?.length && (
          <div className="tabela-rolagem">
            <table className="tabela">
              <thead>
                <tr>
                  <th>Período</th>
                  <th>Motivo</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {(ausencias as Ausencia[]).map((a) => (
                  <tr key={a.id}>
                    <td>{descreverAusencia(a)}</td>
                    <td>{a.motivo || '—'}</td>
                    <td className="numero">
                      {pode && (
                        <form action={removerAusencia.bind(null, id, a.id)}>
                          <button className="btn btn--texto btn--pequeno" type="submit">
                            Remover
                          </button>
                        </form>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {pode && <FormAusencia barbeiroId={id} />}
      </section>
    </Pagina>
  )
}
