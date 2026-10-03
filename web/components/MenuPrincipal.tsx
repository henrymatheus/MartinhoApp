'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

/** O menu do topo; o item da seção atual fica sublinhado em dourado. */
export function MenuPrincipal({ itens }: { itens: { href: string; texto: string }[] }) {
  const caminho = usePathname()
  const ativo = (href: string) =>
    href === '/' ? caminho === '/' || caminho.startsWith('/agendamentos') : caminho.startsWith(href) || (href === '/balanco' && caminho.startsWith('/atendimentos'))
  return (
    <nav className="nav" aria-label="Principal">
      {itens.map((item) => (
        <Link key={item.href} href={item.href} aria-current={ativo(item.href) ? 'page' : undefined}>
          {item.texto}
        </Link>
      ))}
    </nav>
  )
}
