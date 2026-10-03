import 'server-only'
import type { SessaoDaBarbearia } from '@/lib/sessao'

/** As listas do formulário: só itens desta barbearia (RLS) e só os ativos. */
export async function opcoesDoFormulario({ supabase }: SessaoDaBarbearia) {
  const [clientes, barbeiros, servicos] = await Promise.all([
    supabase.from('clientes').select('id, nome').order('nome'),
    supabase.from('barbeiros').select('id, nome').eq('ativo', true).order('nome'),
    supabase.from('servicos').select('id, nome, duracao_minutos, preco').eq('ativo', true).order('nome'),
  ])
  return { clientes: clientes.data ?? [], barbeiros: barbeiros.data ?? [], servicos: servicos.data ?? [] }
}
