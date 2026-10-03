'use server'

import { revalidatePath } from 'next/cache'
import { redirect } from 'next/navigation'
import { after } from 'next/server'
import { type EstadoFormulario, inteiro, texto, valores } from '@/lib/formularios'
import { notificarNovoAgendamento } from '@/lib/push'
import { clienteDoUsuario } from '@/lib/supabase/servidor'

const MENSAGENS: Record<string, string> = {
  pagina: 'O agendamento online desta barbearia não está disponível.',
  ocupado: 'Esse horário acabou de ser ocupado. Escolha outro, por favor.',
  limite: 'Este telefone já tem 3 horários marcados. Para marcar mais, fale com a barbearia.',
}

/**
 * Confirmação do agendamento pelo cliente.
 *
 * Tudo acontece na função agendar_online do banco, numa transação: confere
 * de novo se o horário está livre, aplica o limite por telefone, acha ou
 * cria o cliente e grava. Se dois clientes confirmarem o mesmo horário no
 * mesmo instante, o banco aceita um e recusa o outro.
 */
export async function agendarOnline(slug: string, _estado: EstadoFormulario, dados: FormData): Promise<EstadoFormulario> {
  const v = valores(dados)
  // Armadilha para robôs: um campo escondido que pessoas não preenchem.
  if (texto(dados, 'site')) redirect(`/agendar/${slug}`)

  const supabase = await clienteDoUsuario()
  const { data: r, error } = await supabase.rpc('agendar_online', {
    p_slug: slug,
    p_barbeiro: inteiro(dados, 'barbeiro'),
    p_servico: inteiro(dados, 'servico'),
    p_inicio: texto(dados, 'inicio'),
    p_nome: texto(dados, 'nome'),
    p_telefone: texto(dados, 'telefone'),
  })
  if (error || !r) return { erro: 'Não foi possível agendar agora. Tente de novo em instantes.', valores: v }
  if (r.erro === 'nome') return { erros: { nome: 'Informe seu nome.' }, valores: v }
  if (r.erro === 'telefone') return { erros: { telefone: 'Confira o número: informe o DDD e o telefone, por exemplo (11) 98765-4321.' }, valores: v }
  if (r.erro) {
    // Os horários livres mudaram: a página é montada de novo com os atuais.
    revalidatePath(`/agendar/${slug}`)
    return { erro: MENSAGENS[r.erro] ?? MENSAGENS.ocupado, valores: v }
  }

  // O aviso ao barbeiro sai depois da resposta ao cliente (after): o
  // cliente não espera o envio, e uma falha no aviso não desfaz o agendamento.
  after(() => notificarNovoAgendamento(r.id))
  redirect(`/agendar/${slug}/confirmado/${r.codigo}`)
}
