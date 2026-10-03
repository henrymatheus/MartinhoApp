'use client'

import { useActionState } from 'react'
import { BotaoCopiar } from '@/components/BotaoCopiar'
import { Campo, ErroGeral } from '@/components/Campo'
import { ESTADO_INICIAL } from '@/lib/formularios'
import { gerarLinkDeSenha, novaBarbearia } from './acoes'

export function FormNovaBarbearia() {
  const [estado, acao, enviando] = useActionState(novaBarbearia, ESTADO_INICIAL)
  const v = estado.valores ?? {}
  const e = estado.erros ?? {}
  return (
    <form className="cartao formulario" action={acao} noValidate>
      <ErroGeral erro={estado.erro} />
      {estado.ok && <p className="mensagem mensagem--success">{estado.ok}</p>}
      <div className="formulario__grade">
        <Campo id="a-nome" rotulo="Nome da barbearia" erro={e.nome}>
          <input id="a-nome" name="nome" maxLength={120} defaultValue={v.nome} />
        </Campo>
        <Campo id="a-slug" rotulo="Endereço da página" erro={e.slug} ajuda="Em branco: gerado pelo nome." opcional>
          <input id="a-slug" name="slug" maxLength={60} defaultValue={v.slug} />
        </Campo>
        <Campo id="a-telefone" rotulo="Telefone" opcional>
          <input id="a-telefone" name="telefone" inputMode="tel" maxLength={20} defaultValue={v.telefone} />
        </Campo>
      </div>
      <div className="formulario__grade">
        <Campo id="a-dono" rotulo="Nome do dono" erro={e.dono}>
          <input id="a-dono" name="dono" maxLength={120} defaultValue={v.dono} />
        </Campo>
        <Campo id="a-email" rotulo="E-mail do dono" erro={e.email}>
          <input id="a-email" name="email" type="email" autoComplete="off" defaultValue={v.email} />
        </Campo>
        <Campo id="a-senha" rotulo="Senha inicial" erro={e.senha}>
          <input id="a-senha" name="senha" type="text" autoComplete="new-password" defaultValue={v.senha} />
        </Campo>
      </div>
      <div className="linha-acoes">
        <button className="btn btn--primario" type="submit" disabled={enviando}>
          Criar barbearia
        </button>
      </div>
    </form>
  )
}

export function FormLinkDeSenha({ email }: { email: string }) {
  const [estado, acao, enviando] = useActionState(gerarLinkDeSenha, ESTADO_INICIAL)
  const link = typeof estado.extra?.link === 'string' ? estado.extra.link : ''
  return (
    <form action={acao} className="formulario">
      <input type="hidden" name="email" value={email} />
      <ErroGeral erro={estado.erro} />
      {link ? (
        <>
          <span className="legenda">{estado.ok}</span>
          <code className="link-gerado">{link}</code>
          <BotaoCopiar texto={link} />
        </>
      ) : (
        <button className="btn btn--texto btn--pequeno" type="submit" disabled={enviando}>
          Gerar link para definir senha
        </button>
      )}
    </form>
  )
}
