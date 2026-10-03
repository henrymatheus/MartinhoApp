import type { Metadata } from 'next'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import { Pagina, Vazio } from '@/components/Pagina'
import { aniversarioEm } from '@/lib/agenda'
import { ddmm, ddmmaaaa, diaLocal, hojeLocal, horaLocal } from '@/lib/datas'
import { exigirBarbearia } from '@/lib/sessao'
import { linkWhatsapp } from '@/lib/telefones'
import type { Cliente } from '@/lib/tipos'

export const metadata: Metadata = { title: 'Cliente' }

const reais = (valor: number) => `R$ ${valor.toFixed(2).replace('.', ',')}`

/** Ficha do cliente: dados, próximos horários e histórico de atendimentos. */
export default async function FichaDoCliente({ params }: PageProps<'/clientes/[id]'>) {
  const { supabase } = await exigirBarbearia()
  const id = Number((await params).id)
  // Cliente de outra barbearia: a RLS não devolve, e a página dá 404.
  const { data: cliente } = Number.isInteger(id) ? await supabase.from('clientes').select('*').eq('id', id).maybeSingle<Cliente>() : { data: null }
  if (!cliente) notFound()

  const [{ data: proximos }, { data: atendimentos }] = await Promise.all([
    supabase
      .from('agendamentos')
      .select('id, inicio, barbeiro:barbeiros(nome), servico:servicos(nome)')
      .eq('cliente_id', id)
      .eq('status', 'agendado')
      .gte('inicio', new Date().toISOString())
      .order('inicio'),
    // Os itens de todos os atendimentos vêm na mesma consulta (embed), sem
    // uma consulta por atendimento.
    supabase
      .from('atendimentos')
      .select('id, data, observacoes, barbeiro:barbeiros(nome), itens:itens_atendimento(descricao, valor)')
      .eq('cliente_id', id)
      .order('data', { ascending: false })
      .order('criado_em', { ascending: false }),
  ])
  type Proximo = { id: number; inicio: string; barbeiro: { nome: string }; servico: { nome: string } }
  type Atendimento = { id: number; data: string; observacoes: string; barbeiro: { nome: string } | null; itens: { descricao: string; valor: number }[] }
  const whatsapp = linkWhatsapp(cliente.telefone)

  return (
    <Pagina>
      <div className="cabecalho">
        <div className="cabecalho__textos">
          <Link className="legenda" href="/clientes">
            Clientes
          </Link>
          <h1 className="titulo">
            {cliente.nome} {aniversarioEm(cliente.data_nascimento, hojeLocal()) && <span className="aniversario">Aniversário hoje</span>}
          </h1>
        </div>
        <div className="linha-acoes">
          {whatsapp && (
            <a className="btn btn--secundario" href={whatsapp} target="_blank" rel="noopener">
              WhatsApp
            </a>
          )}
          <Link className="btn btn--secundario" href={`/clientes/${id}/editar`}>
            Editar
          </Link>
          <Link className="btn btn--secundario" href={`/atendimentos/novo?cliente=${id}`}>
            Registrar atendimento
          </Link>
          <Link className="btn btn--primario" href={`/agendamentos/novo?cliente=${id}`}>
            Agendar
          </Link>
        </div>
      </div>

      <section className="cartao">
        <dl className="dados">
          <div>
            <dt>Telefone</dt>
            <dd>{cliente.telefone || '—'}</dd>
          </div>
          <div>
            <dt>E-mail</dt>
            <dd>{cliente.email || '—'}</dd>
          </div>
          <div>
            <dt>Nascimento</dt>
            <dd>{cliente.data_nascimento ? ddmmaaaa(cliente.data_nascimento) : '—'}</dd>
          </div>
          <div>
            <dt>Endereço</dt>
            <dd>{cliente.endereco || '—'}</dd>
          </div>
          {cliente.observacoes && (
            <div>
              <dt>Observações</dt>
              <dd style={{ whiteSpace: 'pre-line' }}>{cliente.observacoes}</dd>
            </div>
          )}
        </dl>
      </section>

      {!!proximos?.length && (
        <section className="formulario">
          <h2 className="subtitulo">Próximos horários</h2>
          <div className="tabela-rolagem">
            <table className="tabela">
              <thead>
                <tr>
                  <th>Data</th>
                  <th>Serviço</th>
                  <th>Barbeiro</th>
                </tr>
              </thead>
              <tbody>
                {(proximos as unknown as Proximo[]).map((ag) => (
                  <tr key={ag.id}>
                    <td>
                      <Link href={`/?data=${diaLocal(ag.inicio)}`}>
                        {ddmm(diaLocal(ag.inicio))} · {horaLocal(ag.inicio)}
                      </Link>
                    </td>
                    <td>{ag.servico.nome}</td>
                    <td>{ag.barbeiro.nome}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <section className="formulario">
        <h2 className="subtitulo">Histórico de atendimentos</h2>
        {atendimentos?.length ? (
          <div className="tabela-rolagem">
            <table className="tabela">
              <thead>
                <tr>
                  <th>Data</th>
                  <th>Serviços</th>
                  <th>Barbeiro</th>
                  <th className="numero">Valor</th>
                </tr>
              </thead>
              <tbody>
                {(atendimentos as unknown as Atendimento[]).map((at) => (
                  <tr key={at.id}>
                    <td>{ddmmaaaa(at.data)}</td>
                    <td>
                      {at.itens.map((i) => i.descricao).join(', ')}
                      {at.observacoes && (
                        <>
                          <br />
                          <span className="legenda">{at.observacoes}</span>
                        </>
                      )}
                    </td>
                    <td>{at.barbeiro?.nome ?? '—'}</td>
                    <td className="numero">{reais(at.itens.reduce((soma, i) => soma + Number(i.valor), 0))}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Vazio titulo="Nenhum atendimento ainda">
            <p>Quando você concluir um horário na agenda, ele aparece aqui.</p>
          </Vazio>
        )}
      </section>
    </Pagina>
  )
}
