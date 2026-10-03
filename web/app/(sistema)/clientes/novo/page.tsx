import type { Metadata } from 'next'
import { Pagina } from '@/components/Pagina'
import { exigirBarbearia } from '@/lib/sessao'
import { FormCliente } from '../FormCliente'

export const metadata: Metadata = { title: 'Novo cliente' }

export default async function NovoCliente() {
  await exigirBarbearia()
  return (
    <Pagina estreita>
      <div className="cabecalho">
        <h1 className="titulo">Novo cliente</h1>
      </div>
      <FormCliente cliente={null} />
    </Pagina>
  )
}
