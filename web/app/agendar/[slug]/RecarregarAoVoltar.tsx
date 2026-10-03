'use client'

import { useRouter } from 'next/navigation'
import { useEffect } from 'react'

/**
 * App instalado não tem botão de recarregar, e o celular reabre a página
 * que ficou na memória. Ao voltar para a tela depois de 1 minuto, os
 * horários são buscados de novo. Não atualiza se o cliente já começou a
 * digitar o nome ou o WhatsApp.
 */
export function RecarregarAoVoltar() {
  const router = useRouter()
  useEffect(() => {
    let saiuEm: number | null = null
    const digitando = () =>
      Array.from(document.querySelectorAll<HTMLInputElement>('form input[type="text"], form input[type="tel"]')).some((c) => c.value.trim() !== '')
    const atualizar = () => {
      if (!digitando()) router.refresh()
    }
    const aoMudarVisibilidade = () => {
      if (document.hidden) saiuEm = Date.now()
      else if (saiuEm && Date.now() - saiuEm > 60_000) atualizar()
    }
    const aoMostrar = (e: PageTransitionEvent) => {
      if (e.persisted) atualizar()
    }
    document.addEventListener('visibilitychange', aoMudarVisibilidade)
    window.addEventListener('pageshow', aoMostrar)
    return () => {
      document.removeEventListener('visibilitychange', aoMudarVisibilidade)
      window.removeEventListener('pageshow', aoMostrar)
    }
  }, [router])
  return null
}
