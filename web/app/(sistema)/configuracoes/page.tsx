import type { Metadata } from 'next'
import { Pagina } from '@/components/Pagina'
import { exigirDono } from '@/lib/sessao'
import type { Barbeiro, Perfil, Servico } from '@/lib/tipos'
import { removerLogin } from './acoes'
import { FormBarbearia, FormBarbeiro, FormNovoLogin, FormServico } from './Formularios'

export const metadata: Metadata = { title: 'Configurações' }

/** O que no Django ficava no /admin/: dados da barbearia, serviços, barbeiros e logins. */
export default async function Configuracoes() {
  const sessao = await exigirDono()
  const { supabase, barbearia } = sessao
  const [{ data: servicos }, { data: barbeiros }, { data: perfis }] = await Promise.all([
    supabase.from('servicos').select('*').order('ativo', { ascending: false }).order('nome'),
    supabase.from('barbeiros').select('*').order('ativo', { ascending: false }).order('nome'),
    supabase.from('perfis').select('id, nome, papel, barbearia_id, superadmin').eq('barbearia_id', barbearia.id).order('nome'),
  ])
  const logins = ((perfis ?? []) as Perfil[]).map((p) => ({ id: p.id, nome: p.nome || '(sem nome)' }))
  const listaBarbeiros = (barbeiros ?? []) as Barbeiro[]
  const barbeiroDoLogin = (id: string) => listaBarbeiros.find((b) => b.usuario_id === id)?.nome

  return (
    <Pagina>
      <div className="cabecalho">
        <div className="cabecalho__textos">
          <h1 className="titulo">Configurações</h1>
          <p className="legenda">Só o dono da barbearia vê esta tela.</p>
        </div>
      </div>

      <section className="formulario">
        <h2 className="subtitulo">Barbearia</h2>
        <FormBarbearia barbearia={barbearia} />
      </section>

      <section className="formulario">
        <h2 className="subtitulo">Serviços</h2>
        <p className="legenda">Serviço desativado some do agendamento, mas continua no histórico.</p>
        <div className="cartao lista-edicao">
          {((servicos ?? []) as Servico[]).map((s) => (
            <FormServico key={s.id} servico={s} />
          ))}
          <FormServico servico={null} />
        </div>
      </section>

      <section className="formulario">
        <h2 className="subtitulo">Barbeiros</h2>
        <p className="legenda">Barbeiro desativado some da agenda, mas continua no histórico. Os horários ficam em Horários.</p>
        <div className="cartao lista-edicao">
          {listaBarbeiros.map((b) => (
            <FormBarbeiro key={b.id} barbeiro={b} logins={logins} />
          ))}
          <FormBarbeiro barbeiro={null} logins={logins} />
        </div>
      </section>

      <section className="formulario">
        <h2 className="subtitulo">Logins da equipe</h2>
        <div className="tabela-rolagem">
          <table className="tabela">
            <thead>
              <tr>
                <th>Nome</th>
                <th>Papel</th>
                <th>Barbeiro ligado</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {((perfis ?? []) as Perfil[]).map((p) => (
                <tr key={p.id}>
                  <td>{p.nome || '—'}</td>
                  <td>{p.papel === 'dono' ? 'Dono' : 'Barbeiro'}</td>
                  <td>{barbeiroDoLogin(p.id) ?? '—'}</td>
                  <td className="numero">
                    {p.id !== sessao.usuarioId && (
                      <form action={removerLogin.bind(null, p.id)}>
                        <button className="btn btn--texto btn--pequeno" type="submit">
                          Remover acesso
                        </button>
                      </form>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <FormNovoLogin barbeiros={listaBarbeiros.filter((b) => b.ativo && !b.usuario_id)} />
      </section>
    </Pagina>
  )
}
