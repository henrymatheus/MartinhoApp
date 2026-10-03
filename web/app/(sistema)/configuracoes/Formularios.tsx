'use client'

import { useActionState } from 'react'
import { Campo, ErroGeral } from '@/components/Campo'
import { ESTADO_INICIAL, type EstadoFormulario } from '@/lib/formularios'
import type { Barbearia, Barbeiro, Servico } from '@/lib/tipos'
import { novoLogin, salvarBarbearia, salvarBarbeiro, salvarServico } from './acoes'

function Resultado({ estado }: { estado: EstadoFormulario }) {
  return (
    <>
      <ErroGeral erro={estado.erro} />
      {estado.ok && <p className="mensagem mensagem--success">{estado.ok}</p>}
    </>
  )
}

export function FormBarbearia({ barbearia }: { barbearia: Barbearia }) {
  const [estado, acao, enviando] = useActionState(salvarBarbearia, ESTADO_INICIAL)
  const v = { ...(barbearia as unknown as Record<string, string>), ...estado.valores }
  const online = estado.valores ? estado.valores.agendamento_online === 'on' : barbearia.agendamento_online
  const e = estado.erros ?? {}
  return (
    <form className="cartao formulario" action={acao} noValidate>
      <Resultado estado={estado} />
      <div className="formulario__grade">
        <Campo id="b-nome" rotulo="Nome" erro={e.nome}>
          <input id="b-nome" name="nome" maxLength={120} defaultValue={v.nome} />
        </Campo>
        <Campo id="b-telefone" rotulo="Telefone" ajuda="Aparece na página de agendamento para contato." opcional>
          <input id="b-telefone" name="telefone" inputMode="tel" maxLength={20} defaultValue={v.telefone} />
        </Campo>
      </div>
      <Campo id="b-endereco" rotulo="Endereço" opcional>
        <input id="b-endereco" name="endereco" maxLength={255} defaultValue={v.endereco} />
      </Campo>
      <Campo id="b-slug" rotulo="Endereço da página de agendamento" erro={e.slug} ajuda="Fica no link: /agendar/este-texto. Ao mudar, o link antigo para de funcionar.">
        <input id="b-slug" name="slug" maxLength={60} defaultValue={v.slug} />
      </Campo>
      <label className="marcar">
        <input type="checkbox" name="agendamento_online" defaultChecked={online} /> Clientes podem agendar pela página online
      </label>
      <div className="linha-acoes">
        <button className="btn btn--primario" type="submit" disabled={enviando}>
          Salvar
        </button>
      </div>
    </form>
  )
}

export function FormServico({ servico }: { servico: Servico | null }) {
  const [estado, acao, enviando] = useActionState(salvarServico.bind(null, servico?.id ?? null), ESTADO_INICIAL)
  const v = { ...(servico as unknown as Record<string, string>), ...estado.valores }
  const e = estado.erros ?? {}
  const p = servico ? `s${servico.id}` : 's-novo'
  return (
    <form className="formulario" action={acao} noValidate>
      <Resultado estado={estado} />
      <div className="linha-edicao">
        <Campo id={`${p}-nome`} rotulo="Serviço" erro={e.nome}>
          <input id={`${p}-nome`} name="nome" maxLength={120} defaultValue={v.nome} placeholder={servico ? undefined : 'Corte'} />
        </Campo>
        <Campo id={`${p}-preco`} rotulo="Preço (R$)" erro={e.preco}>
          <input id={`${p}-preco`} name="preco" inputMode="decimal" defaultValue={v.preco === undefined ? '' : String(v.preco).replace('.', ',')} />
        </Campo>
        <Campo id={`${p}-duracao`} rotulo="Duração (min)" erro={e.duracao_minutos}>
          <input id={`${p}-duracao`} name="duracao_minutos" type="number" min={5} step={5} defaultValue={v.duracao_minutos ?? 30} />
        </Campo>
        {servico && (
          <label className="marcar">
            <input type="checkbox" name="ativo" defaultChecked={estado.valores ? estado.valores.ativo === 'on' : servico.ativo} /> Ativo
          </label>
        )}
        <button className={`btn ${servico ? 'btn--secundario' : 'btn--primario'}`} type="submit" disabled={enviando}>
          {servico ? 'Salvar' : 'Adicionar'}
        </button>
      </div>
    </form>
  )
}

export function FormBarbeiro({ barbeiro, logins }: { barbeiro: Barbeiro | null; logins: { id: string; nome: string }[] }) {
  const [estado, acao, enviando] = useActionState(salvarBarbeiro.bind(null, barbeiro?.id ?? null), ESTADO_INICIAL)
  const v = { ...(barbeiro as unknown as Record<string, string>), ...estado.valores }
  const e = estado.erros ?? {}
  const p = barbeiro ? `b${barbeiro.id}` : 'b-novo'
  return (
    <form className="formulario" action={acao} noValidate>
      <Resultado estado={estado} />
      <div className="linha-edicao">
        <Campo id={`${p}-nome`} rotulo="Barbeiro" erro={e.nome}>
          <input id={`${p}-nome`} name="nome" maxLength={120} defaultValue={v.nome} />
        </Campo>
        <Campo id={`${p}-telefone`} rotulo="Telefone" opcional>
          <input id={`${p}-telefone`} name="telefone" inputMode="tel" maxLength={20} defaultValue={v.telefone} />
        </Campo>
        <Campo id={`${p}-login`} rotulo="Login" erro={e.usuario_id} ajuda="Para ele ver os próprios horários e o balanço." opcional>
          <select id={`${p}-login`} name="usuario_id" defaultValue={v.usuario_id ?? ''}>
            <option value="">Sem login</option>
            {logins.map((l) => (
              <option key={l.id} value={l.id}>
                {l.nome}
              </option>
            ))}
          </select>
        </Campo>
        {barbeiro && (
          <label className="marcar">
            <input type="checkbox" name="ativo" defaultChecked={estado.valores ? estado.valores.ativo === 'on' : barbeiro.ativo} /> Ativo
          </label>
        )}
        <button className={`btn ${barbeiro ? 'btn--secundario' : 'btn--primario'}`} type="submit" disabled={enviando}>
          {barbeiro ? 'Salvar' : 'Adicionar'}
        </button>
      </div>
    </form>
  )
}

export function FormNovoLogin({ barbeiros }: { barbeiros: { id: number; nome: string }[] }) {
  const [estado, acao, enviando] = useActionState(novoLogin, ESTADO_INICIAL)
  const v = estado.valores ?? {}
  const e = estado.erros ?? {}
  return (
    <form className="cartao formulario" action={acao} noValidate>
      <Resultado estado={estado} />
      <div className="formulario__grade">
        <Campo id="l-nome" rotulo="Nome" erro={e.nome}>
          <input id="l-nome" name="nome" maxLength={120} defaultValue={v.nome} />
        </Campo>
        <Campo id="l-email" rotulo="E-mail" erro={e.email}>
          <input id="l-email" name="email" type="email" autoComplete="off" defaultValue={v.email} />
        </Campo>
        <Campo id="l-senha" rotulo="Senha inicial" erro={e.senha} ajuda="Pelo menos 8 caracteres.">
          <input id="l-senha" name="senha" type="text" autoComplete="new-password" defaultValue={v.senha} />
        </Campo>
        <Campo id="l-papel" rotulo="Papel">
          <select id="l-papel" name="papel" defaultValue={v.papel ?? 'barbeiro'}>
            <option value="barbeiro">Barbeiro (vê a agenda; edita só os próprios horários)</option>
            <option value="dono">Dono (acesso a tudo)</option>
          </select>
        </Campo>
        <Campo id="l-barbeiro" rotulo="Ligar ao barbeiro" opcional>
          <select id="l-barbeiro" name="barbeiro" defaultValue={v.barbeiro ?? ''}>
            <option value="">Nenhum</option>
            {barbeiros.map((b) => (
              <option key={b.id} value={b.id}>
                {b.nome}
              </option>
            ))}
          </select>
        </Campo>
      </div>
      <div className="linha-acoes">
        <button className="btn btn--primario" type="submit" disabled={enviando}>
          Criar login
        </button>
      </div>
    </form>
  )
}
