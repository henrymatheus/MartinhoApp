import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import { Pagina } from '@/components/Pagina'
import { diaLocal, horaLocal } from '@/lib/datas'
import { exigirBarbearia } from '@/lib/sessao'
import { FormAgendamento } from '../../FormAgendamento'
import { opcoesDoFormulario } from '../../opcoes'

export const metadata: Metadata = { title: 'Remarcar' }

export default async function Remarcar({ params }: PageProps<'/agendamentos/[id]/editar'>) {
  const sessao = await exigirBarbearia()
  const id = Number((await params).id)
  // Agendamento de outra barbearia: a RLS não devolve, e a página dá 404.
  const { data: ag } = Number.isInteger(id)
    ? await sessao.supabase.from('agendamentos').select('*, cliente:clientes(nome)').eq('id', id).maybeSingle()
    : { data: null }
  if (!ag) notFound()
  const opcoes = await opcoesDoFormulario(sessao)
  // Barbeiro ou serviço desativado depois de agendado continua aparecendo na lista.
  const { data: atuais } = await sessao.supabase.from('servicos').select('id, nome, duracao_minutos, preco').eq('id', ag.servico_id)
  const { data: barbeiroAtual } = await sessao.supabase.from('barbeiros').select('id, nome').eq('id', ag.barbeiro_id)
  const unir = <T extends { id: number }>(lista: T[], extra: T[] | null) => [...lista, ...(extra ?? []).filter((x) => !lista.some((l) => l.id === x.id))]
  return (
    <Pagina estreita>
      <div className="cabecalho">
        <div className="cabecalho__textos">
          <h1 className="titulo">Remarcar horário</h1>
          <p className="legenda">{(ag.cliente as { nome: string }).nome}</p>
        </div>
      </div>
      <FormAgendamento
        id={id}
        clientes={opcoes.clientes}
        barbeiros={unir(opcoes.barbeiros, barbeiroAtual)}
        servicos={unir(opcoes.servicos, atuais)}
        inicial={{
          cliente: String(ag.cliente_id),
          barbeiro: String(ag.barbeiro_id),
          servico: String(ag.servico_id),
          data: diaLocal(ag.inicio),
          hora: horaLocal(ag.inicio),
          observacoes: ag.observacoes,
        }}
      />
    </Pagina>
  )
}
