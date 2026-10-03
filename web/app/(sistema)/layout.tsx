import type { Metadata } from 'next'
import Link from 'next/link'
import { sair } from '@/app/entrar/acoes'
import { BotaoAvisos } from '@/components/BotaoAvisos'
import { MenuPrincipal } from '@/components/MenuPrincipal'
import { variavelOpcional } from '@/lib/ambiente'
import { exigirLogin } from '@/lib/sessao'

export const metadata: Metadata = { manifest: '/manifest.webmanifest' }

/** Cabeçalho com a marca e o menu, comum a todas as telas do sistema. */
export default async function LayoutDoSistema({ children }: { children: React.ReactNode }) {
  const sessao = await exigirLogin()
  const chavePush = variavelOpcional('NEXT_PUBLIC_VAPID_PUBLIC_KEY')
  const itens = [
    ...(sessao.barbearia
      ? [
          { href: '/', texto: 'Agenda' },
          { href: '/clientes', texto: 'Clientes' },
          { href: '/horarios', texto: 'Horários' },
          { href: '/balanco', texto: 'Balanço' },
        ]
      : []),
    ...(sessao.ehDono ? [{ href: '/configuracoes', texto: 'Configurações' }] : []),
    ...(sessao.ehSuperadmin ? [{ href: '/admin', texto: 'Administração' }] : []),
  ]
  return (
    <>
      <header className="topo">
        <div className="topo__conteudo">
          <Link className="topo__logo" href="/" aria-label="Martinho, ir para a agenda">
            <picture>
              <source srcSet="/img/martinho-assinatura-branco.svg" media="(prefers-color-scheme: dark)" />
              <img src="/img/martinho-assinatura-azul.svg" alt="Martinho" width={137} height={36} />
            </picture>
          </Link>
          <MenuPrincipal itens={itens} />
          <div className="topo__usuario">
            {chavePush && <BotaoAvisos chave={chavePush} />}
            <Link href="/conta/senha" className="legenda">
              {sessao.perfil?.nome || sessao.email}
              {sessao.barbearia && ` · ${sessao.barbearia.nome}`}
            </Link>
            <form action={sair}>
              <button className="btn btn--texto btn--pequeno" type="submit">
                Sair
              </button>
            </form>
          </div>
        </div>
      </header>
      {children}
    </>
  )
}
