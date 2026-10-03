import type { Metadata } from 'next'
import { Pagina } from '@/components/Pagina'
import { exigirSuperadmin } from '@/lib/sessao'
import { clienteAdmin } from '@/lib/supabase/admin'
import { FormLinkDeSenha, FormNovaBarbearia } from './Formularios'

export const metadata: Metadata = { title: 'Administração' }

/** Painel do superadmin: todas as barbearias (inquilinos) e seus logins. */
export default async function Admin() {
  await exigirSuperadmin()
  const admin = clienteAdmin()
  const [{ data: barbearias }, { data: perfis }, { data: usuarios }] = await Promise.all([
    admin.from('barbearias').select('id, nome, slug, agendamento_online').order('nome'),
    admin.from('perfis').select('id, nome, papel, barbearia_id, superadmin'),
    admin.auth.admin.listUsers({ perPage: 1000 }),
  ])
  const emailDe = (id: string) => usuarios?.users.find((u) => u.id === id)?.email ?? '—'

  return (
    <Pagina>
      <div className="cabecalho">
        <div className="cabecalho__textos">
          <span className="rotulo">Superadmin</span>
          <h1 className="titulo">Administração</h1>
          <p className="legenda">Todas as barbearias que usam o Martinho.</p>
        </div>
      </div>

      <section className="formulario">
        <h2 className="subtitulo">Nova barbearia</h2>
        <FormNovaBarbearia />
      </section>

      {(barbearias ?? []).map((b) => (
        <section key={b.id} className="formulario">
          <div className="cabecalho">
            <div className="cabecalho__textos">
              <h2 className="subtitulo">{b.nome}</h2>
              <a className="legenda" href={`/agendar/${b.slug}`} target="_blank" rel="noopener">
                /agendar/{b.slug}
                {!b.agendamento_online && ' (agendamento online desligado)'}
              </a>
            </div>
          </div>
          <div className="tabela-rolagem">
            <table className="tabela">
              <thead>
                <tr>
                  <th>Nome</th>
                  <th>E-mail</th>
                  <th>Papel</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {(perfis ?? [])
                  .filter((p) => p.barbearia_id === b.id)
                  .map((p) => (
                    <tr key={p.id}>
                      <td>{p.nome || '—'}</td>
                      <td>{emailDe(p.id)}</td>
                      <td>{p.papel === 'dono' ? 'Dono' : 'Barbeiro'}</td>
                      <td>
                        <FormLinkDeSenha email={emailDe(p.id)} />
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </section>
      ))}
    </Pagina>
  )
}
