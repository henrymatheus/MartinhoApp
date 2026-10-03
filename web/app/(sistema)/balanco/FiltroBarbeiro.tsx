'use client'

import { useRouter } from 'next/navigation'

/** Escolha do barbeiro no balanço do dono: troca a página ao escolher. */
export function FiltroBarbeiro({
  parametros,
  barbeiros,
  atual,
}: {
  parametros: Record<string, string>
  barbeiros: { id: number; nome: string; ativo: boolean }[]
  atual: number | null
}) {
  const router = useRouter()
  return (
    <div className="filtro-barbeiro campo">
      <label htmlFor="filtro-barbeiro">Barbeiro</label>
      <select
        id="filtro-barbeiro"
        defaultValue={atual ?? ''}
        onChange={(e) => {
          const ps = new URLSearchParams(parametros)
          if (e.target.value) ps.set('barbeiro', e.target.value)
          router.push(`/balanco?${ps}`)
        }}
      >
        <option value="">Todos os barbeiros</option>
        {barbeiros.map((b) => (
          <option key={b.id} value={b.id}>
            {b.nome}
            {!b.ativo && ' (desativado)'}
          </option>
        ))}
      </select>
    </div>
  )
}
