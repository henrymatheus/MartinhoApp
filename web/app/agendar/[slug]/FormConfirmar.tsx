'use client'

import { useActionState } from 'react'
import { Campo, ErroGeral } from '@/components/Campo'
import { ESTADO_INICIAL } from '@/lib/formularios'
import { agendarOnline } from './acoes'

export function FormConfirmar({ slug, barbeiro, servico, inicio }: { slug: string; barbeiro: number; servico: number; inicio: string }) {
  const [estado, acao, enviando] = useActionState(agendarOnline.bind(null, slug), ESTADO_INICIAL)
  const v = estado.valores ?? {}
  const e = estado.erros ?? {}
  return (
    <form className="formulario" action={acao} noValidate>
      <ErroGeral erro={estado.erro} />
      <input type="hidden" name="barbeiro" value={barbeiro} />
      <input type="hidden" name="servico" value={servico} />
      <input type="hidden" name="inicio" value={inicio} />
      <input type="hidden" name="site" defaultValue="" />
      <Campo id="nome" rotulo="Seu nome" erro={e.nome}>
        <input id="nome" name="nome" type="text" maxLength={120} autoComplete="name" defaultValue={v.nome} />
      </Campo>
      <Campo id="telefone" rotulo="WhatsApp" erro={e.telefone} ajuda="Com DDD. A barbearia usa este número para falar com você.">
        <input id="telefone" name="telefone" type="tel" inputMode="tel" autoComplete="tel" placeholder="(11) 98765-4321" maxLength={20} defaultValue={v.telefone} />
      </Campo>
      <button className="btn btn--primario" type="submit" disabled={enviando}>
        {enviando ? 'Confirmando…' : 'Confirmar agendamento'}
      </button>
    </form>
  )
}
