'use client'

import { useEffect, useState } from 'react'

function paraBytes(base64: string) {
  const pad = '='.repeat((4 - (base64.length % 4)) % 4)
  const bruto = atob((base64 + pad).replace(/-/g, '+').replace(/_/g, '/'))
  return Uint8Array.from(bruto, (c) => c.charCodeAt(0))
}

function enviar(inscricao: PushSubscription) {
  return fetch('/api/avisos', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(inscricao) })
}

/**
 * Botão "Ativar avisos": pede permissão, inscreve este aparelho no push e
 * manda a inscrição para o servidor. Some quando o aparelho já está inscrito.
 */
export function BotaoAvisos({ chave }: { chave: string }) {
  const [visivel, setVisivel] = useState(false)
  const [texto, setTexto] = useState('Ativar avisos')
  const [ocupado, setOcupado] = useState(false)

  useEffect(() => {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) return
    navigator.serviceWorker.ready.then((reg) =>
      reg.pushManager.getSubscription().then((atual) => {
        if (atual) {
          // Já inscrito: reenvia, para o servidor saber de quem é o aparelho agora.
          enviar(atual)
          return
        }
        if (Notification.permission !== 'denied') setVisivel(true)
      }),
    )
  }, [])

  async function ativar() {
    setOcupado(true)
    try {
      const permissao = await Notification.requestPermission()
      if (permissao !== 'granted') {
        setTexto('Avisos bloqueados')
        return
      }
      const reg = await navigator.serviceWorker.ready
      const inscricao = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: paraBytes(chave) })
      await enviar(inscricao)
      setTexto('Avisos ativos')
      setTimeout(() => setVisivel(false), 2500)
    } catch {
      setOcupado(false)
      setTexto('Tentar de novo')
    }
  }

  if (!visivel) return null
  return (
    <button className="btn btn--secundario btn--pequeno" type="button" onClick={ativar} disabled={ocupado}>
      {texto}
    </button>
  )
}
