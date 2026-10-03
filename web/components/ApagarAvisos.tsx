'use client'

import { useEffect } from 'react'

/** Apaga o cookie das mensagens depois que elas apareceram na tela. */
export function ApagarAvisos() {
  useEffect(() => {
    document.cookie = 'martinho_avisos=; Max-Age=0; path=/; SameSite=Lax'
  }, [])
  return null
}
