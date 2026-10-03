import type { Metadata, Viewport } from 'next'
import { Bodoni_Moda, Figtree } from 'next/font/google'
import { RegistrarServiceWorker } from '@/components/RegistrarServiceWorker'
import './estilos/tokens.css'
import './estilos/martinho.css'
import './estilos/extras.css'

// As fontes são baixadas no build e servidas pelo próprio site (sem
// pedido ao Google no celular do cliente). As variáveis CSS abaixo
// substituem as famílias de tokens.css (ver extras.css).
const marca = Bodoni_Moda({ subsets: ['latin'], axes: ['opsz'], variable: '--fonte-marca', display: 'swap' })
const texto = Figtree({ subsets: ['latin'], variable: '--fonte-texto', display: 'swap' })

export const metadata: Metadata = {
  title: { template: '%s · Martinho', default: 'Martinho' },
  icons: { icon: { url: '/img/martinho-simbolo.svg', type: 'image/svg+xml' }, apple: '/img/icone-180.png' },
}

export const viewport: Viewport = {
  themeColor: '#0e2240',
  viewportFit: 'cover',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-br" className={`${marca.variable} ${texto.variable}`}>
      <body>
        {children}
        <RegistrarServiceWorker />
      </body>
    </html>
  )
}
