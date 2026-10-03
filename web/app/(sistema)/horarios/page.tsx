import type { Metadata } from 'next'
import Link from 'next/link'
import { redirect } from 'next/navigation'
import { BotaoCopiar } from '@/components/BotaoCopiar'
import { Pagina, Vazio } from '@/components/Pagina'
import { hhmm } from '@/lib/agenda'
import { NOMES_DOS_DIAS } from '@/lib/datas'
import { exigirBarbearia, podeEditarBarbeiro } from '@/lib/sessao'
import { urlDoSite } from '@/lib/site'
import type { HorarioTrabalho } from '@/lib/tipos'

export const metadata: Metadata = { title: 'Horários' }

/** Lista dos barbeiros com o resumo dos horários e o link da página de agendamento. */
export default async function Horarios() {
  const sessao = await exigirBarbearia()
  const { supabase, barbearia, meuBarbeiro } = sessao
  // O barbeiro vai direto para os próprios horários.
  if (sessao.ehBarbeiro && meuBarbeiro) redirect(`/horarios/${meuBarbeiro.id}`)

  const { data } = await supabase
    .from('barbeiros')
    .select('id, nome, horarios:horarios_trabalho(id, barbeiro_id, dia_semana, inicio, fim)')
    .eq('ativo', true)
    .order('nome')
  const barbeiros = (data ?? []) as unknown as { id: number; nome: string; horarios: HorarioTrabalho[] }[]
  const linkPublico = `${await urlDoSite()}/agendar/${barbearia.slug}`

  return (
    <Pagina>
      <div className="cabecalho">
        <div className="cabecalho__textos">
          <h1 className="titulo">Horários de atendimento</h1>
          <p className="legenda">Os clientes só conseguem agendar dentro destes horários.</p>
        </div>
      </div>

      <section className="cartao formulario">
        <div className="cabecalho__textos">
          <h2 className="subtitulo">Página de agendamento</h2>
          <p className="legenda">
            {barbearia.agendamento_online
              ? 'Envie este link aos clientes ou coloque na bio do Instagram. Pelo celular, dá para instalar a página como app.'
              : 'O agendamento online está desligado. O dono liga em Configurações.'}
          </p>
        </div>
        <div className="linha-acoes">
          <input className="campo-copiar" id="link-publico" defaultValue={linkPublico} readOnly aria-label="Link da página de agendamento" />
          <BotaoCopiar texto={linkPublico} />
          <a className="btn btn--secundario" href={linkPublico} target="_blank" rel="noopener">
            Abrir
          </a>
        </div>
      </section>

      {barbeiros.length ? (
        <div className="tabela-rolagem">
          <table className="tabela">
            <thead>
              <tr>
                <th>Barbeiro</th>
                <th>Dias e horários</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {barbeiros.map((b) => {
                const turnos = [...b.horarios].sort((x, y) => x.dia_semana - y.dia_semana || x.inicio.localeCompare(y.inicio))
                return (
                  <tr key={b.id}>
                    <td>
                      <Link href={`/horarios/${b.id}`}>{b.nome}</Link>
                    </td>
                    <td>
                      {turnos.length ? (
                        turnos.map((h) => (
                          <div key={h.id}>
                            {NOMES_DOS_DIAS[h.dia_semana]} {hhmm(h.inicio)}-{hhmm(h.fim)}
                          </div>
                        ))
                      ) : (
                        <span className="legenda">Sem horários: não aparece para os clientes</span>
                      )}
                    </td>
                    <td className="numero">
                      <Link className="btn btn--secundario btn--pequeno" href={`/horarios/${b.id}`}>
                        {podeEditarBarbeiro(sessao, b.id) ? 'Editar' : 'Ver'}
                      </Link>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <Vazio titulo="Nenhum barbeiro ativo">
          <p>Cadastre os barbeiros em Configurações.</p>
        </Vazio>
      )}
    </Pagina>
  )
}
