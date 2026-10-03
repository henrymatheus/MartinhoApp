'use client'

export function BotaoRecarregar() {
  return (
    <button className="btn btn--primario" type="button" onClick={() => location.reload()}>
      Tentar de novo
    </button>
  )
}
