import { lerAvisos } from '@/lib/avisos'
import { ApagarAvisos } from './ApagarAvisos'

// Mesmas classes do Django (mensagem--success etc.).
const CLASSE = { sucesso: 'success', erro: 'error', alerta: 'warning' } as const

export async function Avisos() {
  const { avisos, bruto } = await lerAvisos()
  if (!avisos.length) return null
  return (
    <>
      <ul className="mensagens" role="status">
        {avisos.map((a, i) => (
          <li key={i} className={`mensagem mensagem--${CLASSE[a.tipo] ?? 'info'}`}>
            {a.texto}
          </li>
        ))}
      </ul>
      {/* key: uma mensagem nova remonta o componente, que apaga de novo. */}
      <ApagarAvisos key={bruto} />
    </>
  )
}
