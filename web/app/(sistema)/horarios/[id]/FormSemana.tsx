'use client'

import { useActionState } from 'react'
import { ErroGeral } from '@/components/Campo'
import { NOMES_DOS_DIAS } from '@/lib/datas'
import { ESTADO_INICIAL } from '@/lib/formularios'
import { salvarSemana } from '../acoes'

/** Uma linha por dia: "atende?" + manhã + tarde (opcional). */
export function FormSemana({ barbeiroId, inicial }: { barbeiroId: number; inicial: Record<string, string> }) {
  const [estado, acao, enviando] = useActionState(salvarSemana.bind(null, barbeiroId), ESTADO_INICIAL)
  // Depois de um erro, o formulário volta com o que foi digitado.
  const v = estado.valores ?? inicial
  return (
    <form className="cartao formulario" action={acao} noValidate>
      <ErroGeral erro={estado.erro} />
      <div className="tabela-rolagem">
        <table className="tabela tabela--semana">
          <thead>
            <tr>
              <th>Dia</th>
              <th>Manhã</th>
              <th>
                Tarde <span className="legenda">(opcional)</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {NOMES_DOS_DIAS.map((nome, dia) => (
              <tr key={dia}>
                <td>
                  <label className="marcar">
                    <input type="checkbox" name={`d${dia}_ativo`} defaultChecked={v[`d${dia}_ativo`] === 'on'} /> {nome}
                  </label>
                </td>
                {[1, 2].map((n) => (
                  <td key={n}>
                    <div className="turno">
                      <input type="time" step={900} name={`d${dia}_inicio${n}`} aria-label={`${nome}, início`} defaultValue={v[`d${dia}_inicio${n}`]} />
                      <span aria-hidden="true">às</span>
                      <input type="time" step={900} name={`d${dia}_fim${n}`} aria-label={`${nome}, fim`} defaultValue={v[`d${dia}_fim${n}`]} />
                    </div>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="linha-acoes">
        <button className="btn btn--primario" type="submit" disabled={enviando}>
          Salvar horários
        </button>
      </div>
    </form>
  )
}
