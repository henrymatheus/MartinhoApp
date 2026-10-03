'use client'

import Link from 'next/link'
import { useActionState } from 'react'
import { Campo, ErroGeral } from '@/components/Campo'
import { ESTADO_INICIAL } from '@/lib/formularios'
import type { Cliente } from '@/lib/tipos'
import { salvarCliente } from './acoes'

export function FormCliente({ cliente }: { cliente: Cliente | null }) {
  const [estado, acao, enviando] = useActionState(salvarCliente.bind(null, cliente?.id ?? null), ESTADO_INICIAL)
  const v = { ...(cliente as unknown as Record<string, string>), ...estado.valores }
  const e = estado.erros ?? {}
  return (
    <form className="cartao formulario" action={acao} noValidate>
      <ErroGeral erro={estado.erro} />
      <Campo id="nome" rotulo="Nome" erro={e.nome}>
        <input id="nome" name="nome" maxLength={120} defaultValue={v.nome} />
      </Campo>
      <div className="formulario__grade">
        <Campo id="telefone" rotulo="Telefone" erro={e.telefone} ajuda="Com DDD. Usado para os lembretes no WhatsApp." opcional>
          <input id="telefone" name="telefone" inputMode="tel" placeholder="(11) 98765-4321" maxLength={20} defaultValue={v.telefone} />
        </Campo>
        <Campo id="data_nascimento" rotulo="Data de nascimento" erro={e.data_nascimento} ajuda="Para o aviso de aniversário." opcional>
          <input id="data_nascimento" name="data_nascimento" type="date" defaultValue={v.data_nascimento ?? ''} />
        </Campo>
      </div>
      <Campo id="email" rotulo="E-mail" erro={e.email} opcional>
        <input id="email" name="email" type="email" inputMode="email" defaultValue={v.email} />
      </Campo>
      <Campo id="endereco" rotulo="Endereço" erro={e.endereco} opcional>
        <input id="endereco" name="endereco" maxLength={255} defaultValue={v.endereco} />
      </Campo>
      <Campo id="observacoes" rotulo="Observações" opcional>
        <textarea id="observacoes" name="observacoes" rows={3} defaultValue={v.observacoes} />
      </Campo>
      <div className="linha-acoes">
        <button className="btn btn--primario" type="submit" disabled={enviando}>
          {cliente ? 'Salvar' : 'Cadastrar'}
        </button>
        <Link className="btn btn--secundario" href={cliente ? `/clientes/${cliente.id}` : '/clientes'}>
          Voltar
        </Link>
      </div>
    </form>
  )
}
