'use client'

import Link from 'next/link'
import { useActionState } from 'react'
import { ErroGeral } from '@/components/Campo'
import { ESTADO_INICIAL } from '@/lib/formularios'
import { entrar } from './acoes'

export function FormEntrar({ proximo }: { proximo: string }) {
  const [estado, acao, enviando] = useActionState(entrar, ESTADO_INICIAL)
  return (
    <form className="cartao formulario" action={acao}>
      <ErroGeral erro={estado.erro} />
      <div className="campo">
        <label htmlFor="email">E-mail</label>
        <input id="email" name="email" type="email" autoComplete="username" autoCapitalize="none" required autoFocus defaultValue={estado.valores?.email} />
      </div>
      <div className="campo">
        <label htmlFor="senha">Senha</label>
        <input id="senha" name="senha" type="password" autoComplete="current-password" required />
      </div>
      <input type="hidden" name="proximo" value={proximo} />
      <button className="btn btn--primario" type="submit" disabled={enviando}>
        Entrar
      </button>
      <Link className="legenda" href="/entrar/esqueci">
        Esqueci minha senha
      </Link>
    </form>
  )
}
