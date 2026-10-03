'use client'

import Link from 'next/link'
import { useActionState } from 'react'
import { Campo, ErroGeral } from '@/components/Campo'
import { ESTADO_INICIAL } from '@/lib/formularios'
import { registrarAtendimento } from './acoes'

interface Opcao {
  id: number
  nome: string
}

export function FormAtendimento({ clientes, barbeiros, inicial }: { clientes: Opcao[]; barbeiros: Opcao[]; inicial: Record<string, string> }) {
  const [estado, acao, enviando] = useActionState(registrarAtendimento, ESTADO_INICIAL)
  const v = { ...inicial, ...estado.valores }
  const e = estado.erros ?? {}
  const unico = barbeiros.length === 1 ? barbeiros[0] : null
  return (
    <form className="cartao formulario" action={acao} noValidate>
      <ErroGeral erro={estado.erro} />
      <fieldset className="grupo">
        <legend className="corpo-forte">Cliente</legend>
        <Campo id="cliente" rotulo="Cliente cadastrado">
          <select id="cliente" name="cliente" defaultValue={v.cliente ?? ''}>
            <option value="">Escolha um cliente</option>
            {clientes.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nome}
              </option>
            ))}
          </select>
        </Campo>
        <details className="cliente-novo" open={Boolean(v.novo_nome)}>
          <summary>Não está na lista? Cadastrar cliente novo</summary>
          <div className="formulario">
            <Campo id="novo_nome" rotulo="Nome">
              <input id="novo_nome" name="novo_nome" maxLength={120} defaultValue={v.novo_nome} />
            </Campo>
            <Campo id="novo_telefone" rotulo="WhatsApp" ajuda="Se o número já estiver cadastrado, o atendimento vai para a ficha existente." opcional>
              <input id="novo_telefone" name="novo_telefone" inputMode="tel" placeholder="(11) 98765-4321" maxLength={20} defaultValue={v.novo_telefone} />
            </Campo>
          </div>
        </details>
      </fieldset>

      {unico ? (
        <>
          <input type="hidden" name="barbeiro" value={unico.id} />
          <p className="legenda">
            Barbeiro: <span className="corpo-forte">{unico.nome}</span>
          </p>
        </>
      ) : (
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
      )}

      <Campo id="data" rotulo="Data" erro={e.data}>
        <input id="data" name="data" type="date" defaultValue={v.data} />
      </Campo>
      <Campo id="observacoes" rotulo="Observações" opcional>
        <textarea id="observacoes" name="observacoes" rows={2} defaultValue={v.observacoes} />
      </Campo>
      <div className="linha-acoes">
        <button className="btn btn--primario" type="submit" disabled={enviando}>
          Registrar
        </button>
        <Link className="btn btn--secundario" href="/balanco">
          Voltar
        </Link>
      </div>
    </form>
  )
}
