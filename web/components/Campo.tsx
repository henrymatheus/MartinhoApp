/**
 * Um campo de formulário com rótulo, ajuda e erro (o includes/campo.html
 * do Django). O <input> vem como filho, com id igual a `id`.
 */
export function Campo({
  id,
  rotulo,
  erro,
  ajuda,
  opcional = false,
  children,
}: {
  id: string
  rotulo: string
  erro?: string
  ajuda?: string
  opcional?: boolean
  children: React.ReactNode
}) {
  return (
    <div className={`campo${erro ? ' campo--erro' : ''}`}>
      <label htmlFor={id}>
        {rotulo}
        {opcional && <span className="legenda"> (opcional)</span>}
      </label>
      {children}
      {erro ? <span className="campo__erro">{erro}</span> : ajuda ? <span className="campo__ajuda">{ajuda}</span> : null}
    </div>
  )
}

export function ErroGeral({ erro }: { erro?: string }) {
  return erro ? <p className="erro-geral">{erro}</p> : null
}

export const Seta = {
  Esquerda: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="m15 18-6-6 6-6" />
    </svg>
  ),
  Direita: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="m9 18 6-6-6-6" />
    </svg>
  ),
}
