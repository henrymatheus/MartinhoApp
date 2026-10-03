'use client'

import { useState } from 'react'

export function BotaoCopiar({ texto, rotulo = 'Copiar link' }: { texto: string; rotulo?: string }) {
  const [copiado, setCopiado] = useState(false)
  return (
    <button
      className="btn btn--secundario"
      type="button"
      onClick={() => navigator.clipboard?.writeText(texto).then(() => setCopiado(true))}
    >
      {copiado ? 'Copiado' : rotulo}
    </button>
  )
}
