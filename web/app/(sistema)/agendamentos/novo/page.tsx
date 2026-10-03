import type { Metadata } from 'next'
import { Pagina } from '@/components/Pagina'
import { hojeLocal, lerDia } from '@/lib/datas'
import { exigirBarbearia } from '@/lib/sessao'
import { FormAgendamento } from '../FormAgendamento'
import { opcoesDoFormulario } from '../opcoes'

export const metadata: Metadata = { title: 'Novo agendamento' }

export default async function NovoAgendamento({ searchParams }: PageProps<'/agendamentos/novo'>) {
  const sessao = await exigirBarbearia()
  const { data, cliente } = await searchParams
  // A partir da agenda de um dia, o formulário já vem com aquela data; a
  // partir da ficha de um cliente, já vem com o cliente escolhido.
  const inicial = { data: lerDia(data) ?? hojeLocal(), cliente: typeof cliente === 'string' ? cliente : '' }
  return (
    <Pagina estreita>
      <div className="cabecalho">
        <div className="cabecalho__textos">
          <h1 className="titulo">Novo agendamento</h1>
        </div>
      </div>
      <FormAgendamento id={null} inicial={inicial} {...await opcoesDoFormulario(sessao)} />
    </Pagina>
  )
}
