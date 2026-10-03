import type { Metadata } from 'next'
import Link from 'next/link'
import { Pagina, Vazio } from '@/components/Pagina'
import { hojeLocal } from '@/lib/datas'
import { exigirBarbearia } from '@/lib/sessao'
import { FormAtendimento } from './FormAtendimento'

export const metadata: Metadata = { title: 'Registrar atendimento' }

/** Atendimento de quem chegou sem hora marcada: vai direto para o histórico e o balanço. */
export default async function RegistrarAtendimento({ searchParams }: PageProps<'/atendimentos/novo'>) {
  const sessao = await exigirBarbearia()
  const { cliente } = await searchParams
  const [{ data: clientes }, { data: barbeiros }] = await Promise.all([
    sessao.supabase.from('clientes').select('id, nome').order('nome'),
    sessao.supabase.from('barbeiros').select('id, nome').eq('ativo', true).order('nome'),
  ])
  // O dono registra para qualquer barbeiro ativo; o barbeiro, só para si.
  const possiveis = sessao.ehBarbeiro ? (barbeiros ?? []).filter((b) => b.id === sessao.meuBarbeiro?.id) : (barbeiros ?? [])
  return (
    <Pagina estreita>
      <div className="cabecalho">
        <div className="cabecalho__textos">
          <Link className="legenda" href="/balanco">
            Balanço
          </Link>
          <h1 className="titulo">Registrar atendimento</h1>
          <p className="legenda">Para quem chegou sem hora marcada. Entra no histórico do cliente e no balanço.</p>
        </div>
      </div>
      {sessao.ehBarbeiro && !possiveis.length ? (
        <Vazio titulo="Seu login ainda não está ligado a um barbeiro">
          <p>Peça ao dono da barbearia para ligar o seu usuário à sua ficha de barbeiro.</p>
        </Vazio>
      ) : (
        <FormAtendimento
          clientes={clientes ?? []}
          barbeiros={possiveis}
          inicial={{ cliente: typeof cliente === 'string' ? cliente : '', data: hojeLocal(), barbeiro: possiveis.length === 1 ? String(possiveis[0].id) : '' }}
        />
      )}
    </Pagina>
  )
}
