import type { Metadata } from 'next'
import Link from 'next/link'
import { Pagina, Vazio } from '@/components/Pagina'
import { ddmm } from '@/lib/datas'
import { exigirBarbearia } from '@/lib/sessao'

export const metadata: Metadata = { title: 'Clientes' }

const POR_PAGINA = 50

export default async function Clientes({ searchParams }: PageProps<'/clientes'>) {
  const { supabase } = await exigirBarbearia()
  const sp = await searchParams
  const busca = (typeof sp.q === 'string' ? sp.q : '').trim()
  const pagina = Math.max(1, Number(sp.page) || 1)

  let consulta = supabase.from('clientes').select('id, nome, telefone, data_nascimento', { count: 'exact' }).order('nome')
  if (busca) {
    // ilike: não diferencia maiúsculas de minúsculas. Vírgulas, parênteses
    // e aspas são retirados porque têm significado no filtro "or" da API.
    const termo = busca.replace(/[,()"\\%*]/g, ' ').trim()
    consulta = consulta.or(`nome.ilike."%${termo}%",telefone.ilike."%${termo}%"`)
  }
  const { data: clientes, count } = await consulta.range((pagina - 1) * POR_PAGINA, pagina * POR_PAGINA - 1)
  const total = count ?? 0
  const paginas = Math.max(1, Math.ceil(total / POR_PAGINA))
  const plural = total === 1 ? '' : 's'
  const urlDaPagina = (n: number) => `/clientes?${new URLSearchParams({ q: busca, page: String(n) })}`

  return (
    <Pagina>
      <div className="cabecalho">
        <div className="cabecalho__textos">
          <h1 className="titulo">Clientes</h1>
          <p className="legenda">
            {total} cliente{plural}
            {busca && ` encontrado${plural} para "${busca}"`}
          </p>
        </div>
        <div className="linha-acoes">
          <form className="busca" method="get" role="search">
            <input id="busca" name="q" defaultValue={busca} placeholder="Nome ou telefone" aria-label="Buscar cliente" />
            <button className="btn btn--secundario" type="submit">
              Buscar
            </button>
          </form>
          <Link className="btn btn--primario" href="/clientes/novo">
            Novo cliente
          </Link>
        </div>
      </div>

      {clientes?.length ? (
        <>
          <div className="tabela-rolagem">
            <table className="tabela">
              <thead>
                <tr>
                  <th>Nome</th>
                  <th>Telefone</th>
                  <th>Aniversário</th>
                </tr>
              </thead>
              <tbody>
                {clientes.map((c) => (
                  <tr key={c.id}>
                    <td>
                      <Link href={`/clientes/${c.id}`}>{c.nome}</Link>
                    </td>
                    <td>{c.telefone || '—'}</td>
                    <td>{c.data_nascimento ? ddmm(c.data_nascimento) : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {paginas > 1 && (
            <nav className="linha-acoes" aria-label="Páginas">
              {pagina > 1 && (
                <Link className="btn btn--secundario" href={urlDaPagina(pagina - 1)}>
                  Anteriores
                </Link>
              )}
              <span className="legenda">
                Página {pagina} de {paginas}
              </span>
              {pagina < paginas && (
                <Link className="btn btn--secundario" href={urlDaPagina(pagina + 1)}>
                  Próximos
                </Link>
              )}
            </nav>
          )}
        </>
      ) : busca ? (
        <Vazio titulo={`Nenhum cliente encontrado para "${busca}"`}>
          <p>Confira a grafia ou busque pelo telefone.</p>
          <Link className="btn btn--secundario" href="/clientes">
            Ver todos
          </Link>
        </Vazio>
      ) : (
        <Vazio titulo="Nenhum cliente cadastrado ainda">
          <p>Cadastre o primeiro para começar a agendar.</p>
          <Link className="btn btn--primario" href="/clientes/novo">
            Novo cliente
          </Link>
        </Vazio>
      )}
    </Pagina>
  )
}
