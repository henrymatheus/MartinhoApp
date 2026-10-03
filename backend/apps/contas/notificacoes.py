"""
Notificações push: o aviso que aparece no celular do barbeiro, igual a uma
notificação de WhatsApp, mesmo com o Martinho fechado.

Funciona pelo padrão Web Push, gratuito, sem serviço pago no meio: o servidor
assina a mensagem com as chaves VAPID (variáveis de ambiente) e a entrega ao
serviço de push do próprio navegador (Google, Apple ou Mozilla).

Se as chaves não estiverem configuradas, nada é enviado e nada quebra.
"""

import json
import logging

from django.conf import settings
from django.utils import timezone

from .models import InscricaoPush, Usuario

logger = logging.getLogger(__name__)


def push_configurado():
    return bool(settings.VAPID_PUBLIC_KEY and settings.VAPID_PRIVATE_KEY)


def enviar(usuarios, titulo, corpo, url='/'):
    """Envia a notificação para todos os aparelhos inscritos desses usuários."""
    if not push_configurado():
        return 0
    from py_vapid import Vapid01
    from pywebpush import WebPushException, webpush

    chave = Vapid01.from_raw(settings.VAPID_PRIVATE_KEY.encode())
    mensagem = json.dumps({'titulo': titulo, 'corpo': corpo, 'url': url})
    enviados = 0
    for inscricao in InscricaoPush.objects.filter(usuario__in=usuarios):
        try:
            webpush(
                subscription_info={
                    'endpoint': inscricao.endpoint,
                    'keys': {'p256dh': inscricao.p256dh, 'auth': inscricao.auth},
                },
                data=mensagem,
                vapid_private_key=chave,
                vapid_claims={'sub': settings.VAPID_EMAIL},
                timeout=5,
            )
            enviados += 1
        except WebPushException as erro:
            status = getattr(erro.response, 'status_code', None)
            if status in (404, 410):
                # O aparelho cancelou a inscrição (app desinstalado, permissão
                # retirada): apagamos para não tentar de novo.
                inscricao.delete()
            else:
                logger.warning('Falha ao enviar push para %s: %s', inscricao, erro)
        except Exception:  # noqa: BLE001 - o aviso nunca pode derrubar o agendamento
            logger.exception('Erro inesperado ao enviar push para %s', inscricao)
    return enviados


def destinatarios(agendamento):
    """
    Quem recebe o aviso de um novo agendamento: o barbeiro escolhido, se ele
    tiver login. Se não tiver, os donos da barbearia, para ninguém ficar sem saber.
    """
    if agendamento.barbeiro.usuario_id:
        return Usuario.objects.filter(pk=agendamento.barbeiro.usuario_id)
    return Usuario.objects.filter(barbearia=agendamento.barbearia, papel=Usuario.Papel.DONO)


def notificar_novo_agendamento(agendamento):
    inicio = timezone.localtime(agendamento.inicio)
    return enviar(
        destinatarios(agendamento),
        titulo=f'Novo agendamento · {inicio:%d/%m} às {inicio:%H:%M}',
        corpo=f'{agendamento.cliente.nome} marcou {agendamento.servico.nome.lower()} com {agendamento.barbeiro.nome}.',
        url=f'/?data={inicio.date().isoformat()}',
    )
