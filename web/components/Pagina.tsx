import { Avisos } from './Avisos'

/** O miolo de cada tela do sistema, com as mensagens no topo. */
export function Pagina({ children, estreita = false }: { children: React.ReactNode; estreita?: boolean }) {
  return (
    <main className={`pagina${estreita ? ' pagina--estreita' : ''}`}>
      <Avisos />
      {children}
    </main>
  )
}

export function Vazio({ titulo, children }: { titulo: string; children?: React.ReactNode }) {
  return (
    <div className="cartao vazio">
      <p className="subtitulo">{titulo}</p>
      {children}
    </div>
  )
}
