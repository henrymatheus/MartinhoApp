'use client'

import { useActionState } from 'react'
import { Campo, ErroGeral } from '@/components/Campo'
import { ESTADO_INICIAL } from '@/lib/formularios'
import { adicionarAusencia } from '../acoes'

export function FormAusencia({ barbeiroId }: { barbeiroId: number }) {
  const [estado, acao, enviando] = useActionState(adicionarAusencia.bind(null, barbeiroId), ESTADO_INICIAL)
  const v = estado.valores ?? {}
  const e = estado.erros ?? {}
  return (
    <form className="cartao formulario" action={acao} noValidate>
      <ErroGeral erro={estado.erro} />
      <div className="formulario__grade">
        <Campo id="data_inicio" rotulo="De" erro={e.data_inicio}>
          <input id="data_inicio" name="data_inicio" type="date" defaultValue={v.data_inicio} />
        </Campo>
        <Campo id="data_fim" rotulo="Até" erro={e.data_fim} ajuda="Em branco: só um dia." opcional>
          <input id="data_fim" name="data_fim" type="date" defaultValue={v.data_fim} />
        </Campo>
        <Campo id="hora_inicio" rotulo="Das" erro={e.hora_inicio} ajuda="Deixe em branco para o dia inteiro." opcional>
          <input id="hora_inicio" name="hora_inicio" type="time" step={900} defaultValue={v.hora_inicio} />
        </Campo>
        <Campo id="hora_fim" rotulo="Às" erro={e.hora_fim} opcional>
          <input id="hora_fim" name="hora_fim" type="time" step={900} defaultValue={v.hora_fim} />
        </Campo>
        <Campo id="motivo" rotulo="Motivo" opcional>
          <input id="motivo" name="motivo" maxLength={80} placeholder="Folga, férias, consulta…" defaultValue={v.motivo} />
        </Campo>
      </div>
      <div className="linha-acoes">
        <button className="btn btn--secundario" type="submit" disabled={enviando}>
          Adicionar ausência
        </button>
      </div>
    </form>
  )
}
