import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import { Pagina } from '@/components/Pagina'
import { exigirBarbearia } from '@/lib/sessao'
import type { Cliente } from '@/lib/tipos'
import { FormCliente } from '../../FormCliente'

export const metadata: Metadata = { title: 'Editar cliente' }

export default async function EditarCliente({ params }: PageProps<'/clientes/[id]/editar'>) {
  const { supabase } = await exigirBarbearia()
  const id = Number((await params).id)
  const { data: cliente } = Number.isInteger(id)
    ? await supabase.from('clientes').select('*').eq('id', id).maybeSingle<Cliente>()
    : { data: null }
  if (!cliente) notFound()
  return (
    <Pagina estreita>
      <div className="cabecalho">
        <h1 className="titulo">Editar {cliente.nome}</h1>
      </div>
      <FormCliente cliente={cliente} />
    </Pagina>
  )
}
