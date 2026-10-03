import 'server-only'
import webpush from 'web-push'
import { diaLocal, ddmm, horaLocal } from './datas'
import { variavelOpcional } from './ambiente'
import { clienteAdmin } from './supabase/admin'

/**
 * Notificações push: o aviso que aparece no celular do barbeiro, igual a
 * uma notificação de WhatsApp, mesmo com o Martinho fechado.
 *
 * Padrão Web Push, gratuito: o servidor assina a mensagem com as chaves
 * VAPID e a entrega ao serviço de push do próprio navegador (Google,
 * Apple ou Mozilla). As chaves podem ser as mesmas do Django: assim os
 * aparelhos já inscritos continuam recebendo depois da troca.
 *
 * Usa o cliente admin (ignora a RLS) porque quem dispara o aviso é o
 * cliente na página pública, que não tem login, e o aviso vai para outra
 * pessoa (o barbeiro).
 *
 * Sem as chaves configuradas, nada é enviado e nada quebra.
 */
export function pushConfigurado() {
  return Boolean(variavelOpcional('NEXT_PUBLIC_VAPID_PUBLIC_KEY') && variavelOpcional('VAPID_PRIVATE_KEY'))
}

interface Mensagem {
  titulo: string
  corpo: string
  url: string
}

export async function enviar(usuarios: string[], mensagem: Mensagem): Promise<number> {
  if (!pushConfigurado() || usuarios.length === 0) return 0
  const admin = clienteAdmin()
  const { data: inscricoes } = await admin.from('inscricoes_push').select('id, endpoint, p256dh, auth').in('usuario_id', usuarios)
  let enviados = 0
  for (const inscricao of inscricoes ?? []) {
    try {
      await webpush.sendNotification(
        { endpoint: inscricao.endpoint, keys: { p256dh: inscricao.p256dh, auth: inscricao.auth } },
        JSON.stringify(mensagem),
        {
          vapidDetails: {
            subject: variavelOpcional('VAPID_EMAIL') || 'mailto:contato@martinho.app',
            publicKey: variavelOpcional('NEXT_PUBLIC_VAPID_PUBLIC_KEY'),
            privateKey: variavelOpcional('VAPID_PRIVATE_KEY'),
          },
          timeout: 5000,
        },
      )
      enviados++
    } catch (erro) {
      const status = (erro as { statusCode?: number }).statusCode
      if (status === 404 || status === 410) {
        // O aparelho cancelou a inscrição (app desinstalado, permissão
        // retirada): apagamos para não tentar de novo.
        await admin.from('inscricoes_push').delete().eq('id', inscricao.id)
      } else {
        console.warn('Falha ao enviar push', status, (erro as Error).message)
      }
    }
  }
  return enviados
}

/**
 * Quem recebe o aviso de um novo agendamento: o barbeiro escolhido, se ele
 * tiver login. Se não tiver, os donos da barbearia, para ninguém ficar sem saber.
 */
export async function notificarNovoAgendamento(agendamentoId: number) {
  try {
    const admin = clienteAdmin()
    const { data: ag } = await admin
      .from('agendamentos')
      .select('inicio, barbearia_id, cliente:clientes(nome), servico:servicos(nome), barbeiro:barbeiros(nome, usuario_id)')
      .eq('id', agendamentoId)
      .single()
    if (!ag) return 0
    const barbeiro = ag.barbeiro as unknown as { nome: string; usuario_id: string | null }
    let destinatarios: string[]
    if (barbeiro.usuario_id) {
      destinatarios = [barbeiro.usuario_id]
    } else {
      const { data: donos } = await admin.from('perfis').select('id').eq('barbearia_id', ag.barbearia_id).eq('papel', 'dono')
      destinatarios = (donos ?? []).map((d) => d.id)
    }
    const cliente = ag.cliente as unknown as { nome: string }
    const servico = ag.servico as unknown as { nome: string }
    return await enviar(destinatarios, {
      titulo: `Novo agendamento · ${ddmm(diaLocal(ag.inicio))} às ${horaLocal(ag.inicio)}`,
      corpo: `${cliente.nome} marcou ${servico.nome.toLowerCase()} com ${barbeiro.nome}.`,
      url: `/?data=${diaLocal(ag.inicio)}`,
    })
  } catch (erro) {
    // O aviso nunca pode derrubar o agendamento.
    console.error('Erro ao notificar novo agendamento', erro)
    return 0
  }
}
