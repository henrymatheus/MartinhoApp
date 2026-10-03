import type { Metadata } from 'next'
import { redirect } from 'next/navigation'
import { obterSessao } from '@/lib/sessao'
import { FormEntrar } from './FormEntrar'

export const metadata: Metadata = { title: 'Entrar' }

export default async function Entrar({ searchParams }: PageProps<'/entrar'>) {
  if (await obterSessao()) redirect('/')
  const { proximo } = await searchParams
  return (
    <main className="tela-marca">
      <div className="login">
        <div className="login__marca">
          <img src="/img/martinho-simbolo.svg" alt="" width={88} height={88} />
          <h1>Martinho</h1>
          <span className="fio" />
        </div>
        <FormEntrar proximo={typeof proximo === 'string' ? proximo : '/'} />
      </div>
    </main>
  )
}
