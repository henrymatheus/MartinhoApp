import { RecarregarAoVoltar } from './RecarregarAoVoltar'

/** Moldura das páginas públicas (agendamento e confirmação). */
export default function LayoutPublico({ children }: { children: React.ReactNode }) {
  return (
    <div className="publico">
      {children}
      <footer className="publico__rodape">
        <img src="/img/martinho-simbolo.svg" alt="" width={20} height={20} />
        <span>Agendamento pelo Martinho</span>
      </footer>
      <RecarregarAoVoltar />
    </div>
  )
}

