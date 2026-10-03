'use client'

import Link from 'next/link'
import { useActionState } from 'react'
import { Campo, ErroGeral } from '@/components/Campo'
import { ESTADO_INICIAL } from '@/lib/formularios'
import { salvarAgendamento } from './acoes'

interface Opcao {
  id: number
  nome: string
}

export function FormAgendamento({
  id,
  clientes,
  barbeiros,
  servicos,
  inicial,
}: {
  id: number | null
  clientes: Opcao[]
  barbeiros: Opcao[]
  servicos: (Opcao & { duracao_minutos: number; preco: number })[]
  inicial: Record<string, string>
}) {
  const [estado, acao, enviando] = useActionState(salvarAgendamento.bind(null, id), ESTADO_INICIAL)
  const v = { ...inicial, ...estado.valores }
  const e = estado.erros ?? {}
  return (
    <form className="cartao formulario" action={acao} noValidate>
      <ErroGeral erro={estado.erro} />
      <Campo id="cliente" rotulo="Cliente" erro={e.cliente}>
        <select id="cliente" name="cliente" defaultValue={v.cliente ?? ''}>
          <option value="">Escolha o cliente</option>
          {clientes.map((c) => (
            <option key={c.id} value={c.id}>
              {c.nome}
            </option>
          ))}
        </select>
      </Campo>
      {!id && (
        <p className="legenda">
          Cliente novo? <Link href="/clientes/novo">Cadastre primeiro</Link> e volte para agendar.
        </p>
      )}
      <div className="formulario__grade">
        <Campo id="data" rotulo="Data" erro={e.data}>
          <input id="data" name="data" type="date" defaultValue={v.data} />
        </Campo>
        <Campo id="hora" rotulo="Hora" erro={e.hora}>
          <input id="hora" name="hora" type="time" step={300} defaultValue={v.hora} />
        </Campo>
      </div>
      <Campo id="barbeiro" rotulo="Barbeiro" erro={e.barbeiro}>
        <select id="barbeiro" name="barbeiro" defaultValue={v.barbeiro ?? ''}>
          <option value="">Escolha o barbeiro</option>
          {barbeiros.map((b) => (
            <option key={b.id} value={b.id}>
              {b.nome}
            </option>
          ))}
        </select>
      </Campo>
      <Campo id="servico" rotulo="Serviço" erro={e.servico}>
        <select id="servico" name="servico" defaultValue={v.servico ?? ''}>
          <option value="">Escolha o serviço</option>
          {servicos.map((s) => (
            <option key={s.id} value={s.id}>
              {s.nome} · {s.duracao_minutos} min · R$ {Number(s.preco).toFixed(2).replace('.', ',')}
            </option>
          ))}
        </select>
      </Campo>
      <Campo id="observacoes" rotulo="Observações" opcional>
        <textarea id="observacoes" name="observacoes" rows={3} defaultValue={v.observacoes} />
      </Campo>
      {(estado.extra?.ausencia || v.agendar_mesmo_assim) && (
        <label className="marcar">
          <input type="checkbox" name="agendar_mesmo_assim" defaultChecked={v.agendar_mesmo_assim === 'on'} /> Agendar mesmo assim (encaixe)
        </label>
      )}
      <div className="linha-acoes">
        <button className="btn btn--primario" type="submit" disabled={enviando}>
          {id ? 'Salvar' : 'Agendar'}
        </button>
        <Link className="btn btn--secundario" href={v.data ? `/?data=${v.data}` : '/'}>
          Voltar
        </Link>
      </div>
    </form>
  )
}
