import type { Metadata } from 'next'
import { BotaoRecarregar } from './BotaoRecarregar'

export const metadata: Metadata = { title: 'Sem conexão' }

// Página guardada no celular pelo service worker, mostrada quando não há internet.
export default function Offline() {
  return (
    <main className="tela-marca">
      <div className="login">
        <div className="login__marca">
          <img src="/img/martinho-simbolo.svg" alt="" width={72} height={72} />
          <h1>Sem conexão</h1>
          <span className="fio" />
          <p>Não foi possível carregar a página. Confira a internet do celular e tente de novo.</p>
        </div>
        <BotaoRecarregar />
      </div>
    </main>
  )
}
