'use client'

import Link from 'next/link'
import { useActionState } from 'react'
import { Campo } from '@/components/Campo'
import { ESTADO_INICIAL } from '@/lib/formularios'
import { esqueciASenha } from '../acoes'

export default function Esqueci() {
  const [estado, acao, enviando] = useActionState(esqueciASenha, ESTADO_INICIAL)
  return (
    <main className="tela-marca">
      <div className="login">
        <div className="login__marca">
          <img src="/img/martinho-simbolo.svg" alt="" width={72} height={72} />
          <h1>Nova senha</h1>
          <span className="fio" />
        </div>
        <form className="cartao formulario" action={acao}>
          {estado.ok ? (
            <p className="mensagem mensagem--success">{estado.ok}</p>
          ) : (
            <>
              <p>Informe o e-mail do seu login. Enviaremos um link para você criar uma nova senha.</p>
              <Campo id="email" rotulo="E-mail" erro={estado.erros?.email}>
                <input id="email" name="email" type="email" autoComplete="username" required defaultValue={estado.valores?.email} />
              </Campo>
              <button className="btn btn--primario" type="submit" disabled={enviando}>
                Enviar link
              </button>
            </>
          )}
          <Link className="legenda" href="/entrar">
            Voltar para o login
          </Link>
        </form>
      </div>
    </main>
  )
}
