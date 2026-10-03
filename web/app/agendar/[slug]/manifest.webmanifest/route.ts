import { manifesto } from '@/lib/manifesto'
import { clienteDoUsuario } from '@/lib/supabase/servidor'

export async function GET(_pedido: Request, { params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params
  const supabase = await clienteDoUsuario()
  const { data } = await supabase.rpc('barbearia_publica', { p_slug: slug })
  if (!data) return new Response('Não encontrado', { status: 404 })
  return manifesto(`Agendar · ${data.nome}`, String(data.nome).slice(0, 12), `/agendar/${slug}`)
}
