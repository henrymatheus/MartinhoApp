import { Pagina } from '@/components/Pagina'
import { exigirLogin } from '@/lib/sessao'

export default async function SemBarbearia() {
  const sessao = await exigirLogin()
  return (
    <Pagina estreita>
      <div className="cartao formulario">
        <h1 className="titulo">Seu login ainda não está ligado a uma barbearia</h1>
        <p>
          Para usar a agenda e os clientes, o login <strong>{sessao.email}</strong> precisa pertencer a uma barbearia.
        </p>
        <p>Peça ao dono da barbearia (ou ao administrador do Martinho) para fazer essa ligação.</p>
      </div>
    </Pagina>
  )
}
