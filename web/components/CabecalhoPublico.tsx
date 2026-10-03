/** Faixa azul do topo das páginas públicas, com o nome da barbearia. */
export function CabecalhoPublico({ barbearia }: { barbearia: { nome: string; endereco: string } }) {
  return (
    <header className="publico__topo">
      <div className="publico__conteudo">
        <span className="rotulo publico__rotulo">Agendamento online</span>
        <h1 className="publico__nome">{barbearia.nome}</h1>
        {barbearia.endereco && <p className="publico__endereco">{barbearia.endereco}</p>}
      </div>
    </header>
  )
}
