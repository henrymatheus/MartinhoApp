import type { Metadata } from 'next'
import { Pagina } from '@/components/Pagina'
import { exigirLogin } from '@/lib/sessao'
import { FormSenha } from './FormSenha'

export const metadata: Metadata = { title: 'Minha senha' }

export default async function MinhaSenha() {
  const sessao = await exigirLogin()
  return (
    <Pagina estreita>
      <div className="cabecalho">
        <div className="cabecalho__textos">
          <h1 className="titulo">Minha senha</h1>
          <p className="legenda">{sessao.email}</p>
        </div>
      </div>
      <FormSenha />
    </Pagina>
  )
}
