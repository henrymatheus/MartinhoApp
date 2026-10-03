import { obterSessao } from '@/lib/sessao'
import { clienteAdmin } from '@/lib/supabase/admin'

/**
 * Recebe do navegador a inscrição do aparelho nos avisos (POST com JSON)
 * e guarda para o usuário logado. DELETE cancela a inscrição.
 *
 * A gravação usa o cliente admin por um motivo: o mesmo celular pode ter
 * sido inscrito antes por outro login (o dono testou no aparelho do
 * barbeiro, por exemplo). O endereço do aparelho é único, então a
 * inscrição precisa passar para o login atual, e a RLS não deixaria um
 * usuário mexer numa linha de outro. O usuário vem da sessão conferida,
 * nunca do corpo do pedido.
 */
interface Inscricao {
  endpoint?: unknown
  keys?: { p256dh?: unknown; auth?: unknown }
}

export async function POST(pedido: Request) {
  const sessao = await obterSessao()
  if (!sessao?.perfil) return Response.json({ erro: 'Faça login.' }, { status: 401 })
  let dados: Inscricao
  try {
    dados = await pedido.json()
  } catch {
    return Response.json({ erro: 'Inscrição inválida.' }, { status: 400 })
  }
  const { endpoint } = dados
  const p256dh = dados.keys?.p256dh
  const auth = dados.keys?.auth
  if (typeof endpoint !== 'string' || !endpoint.startsWith('https://') || typeof p256dh !== 'string' || typeof auth !== 'string') {
    return Response.json({ erro: 'Inscrição inválida.' }, { status: 400 })
  }
  const { error } = await clienteAdmin()
    .from('inscricoes_push')
    .upsert(
      { endpoint, p256dh, auth, usuario_id: sessao.usuarioId, navegador: (pedido.headers.get('user-agent') ?? '').slice(0, 200) },
      { onConflict: 'endpoint' },
    )
  if (error) return Response.json({ erro: 'Inscrição inválida.' }, { status: 400 })
  return Response.json({ ok: true })
}

export async function DELETE(pedido: Request) {
  const sessao = await obterSessao()
  if (!sessao) return Response.json({ erro: 'Faça login.' }, { status: 401 })
  const dados = (await pedido.json().catch(() => ({}))) as Inscricao
  if (typeof dados.endpoint !== 'string') return Response.json({ erro: 'Inscrição inválida.' }, { status: 400 })
  // Aqui basta o cliente do usuário: a RLS só deixa apagar os próprios aparelhos.
  await sessao.supabase.from('inscricoes_push').delete().eq('endpoint', dados.endpoint)
  return Response.json({ ok: true })
}
