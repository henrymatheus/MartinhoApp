'use client'

import { useActionState } from 'react'
import { Campo, ErroGeral } from '@/components/Campo'
import { ESTADO_INICIAL } from '@/lib/formularios'
import { trocarSenha } from './acoes'

export function FormSenha() {
  const [estado, acao, enviando] = useActionState(trocarSenha, ESTADO_INICIAL)
  return (
    <form className="cartao formulario" action={acao}>
      <ErroGeral erro={estado.erro} />
      {estado.ok && <p className="mensagem mensagem--success">{estado.ok}</p>}
      <Campo id="senha" rotulo="Nova senha" erro={estado.erros?.senha} ajuda="Pelo menos 8 caracteres.">
        <input id="senha" name="senha" type="password" autoComplete="new-password" required minLength={8} />
      </Campo>
      <Campo id="confirmacao" rotulo="Repita a nova senha" erro={estado.erros?.confirmacao}>
        <input id="confirmacao" name="confirmacao" type="password" autoComplete="new-password" required />
      </Campo>
      <div className="linha-acoes">
        <button className="btn btn--primario" type="submit" disabled={enviando}>
          Salvar senha
        </button>
      </div>
    </form>
  )
}
