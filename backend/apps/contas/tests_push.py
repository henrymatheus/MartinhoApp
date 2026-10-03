"""Notificação push ao barbeiro quando o cliente agenda pela página."""

import json
from datetime import time, timedelta
from decimal import Decimal
from unittest import mock

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.agenda.models import Agendamento
from apps.cadastros.models import Barbeiro, Cliente, HorarioTrabalho, Servico

from .models import Barbearia, InscricaoPush, Usuario
from .notificacoes import destinatarios

# Chave de teste (gerada só para os testes; não é usada em lugar nenhum).
CHAVES = {
    'VAPID_PUBLIC_KEY': 'BEiCQ7TJmu334UKDZc7e3wXMdGkkFOvtSJivXaBDQ4qRpMGyER8FReox1hlvJ50gAYEnwA-cMHY4N47VrD4XT2M',
    'VAPID_PRIVATE_KEY': 'Z5uSsQqWn0yYVdF1fQ3x6v1c9z3Yk2Jm4bYp7r8s9tA',
    'VAPID_EMAIL': 'mailto:teste@exemplo.com',
}


class Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.barbearia = Barbearia.objects.create(nome='Barbearia Teste')
        cls.servico = Servico.objects.create(barbearia=cls.barbearia, nome='Corte', preco=Decimal('40'), duracao_minutos=30)
        cls.usuario_ricardo = Usuario.objects.create_user(
            'ricardo', password='senha-de-teste-123', barbearia=cls.barbearia, papel=Usuario.Papel.BARBEIRO
        )
        cls.ricardo = Barbeiro.objects.create(barbearia=cls.barbearia, nome='Ricardo', usuario=cls.usuario_ricardo)
        for dia in range(7):
            HorarioTrabalho.objects.create(barbeiro=cls.ricardo, dia_semana=dia, inicio=time(9), fim=time(18))
        cls.dono = Usuario.objects.create_user('dono', password='senha-de-teste-123', barbearia=cls.barbearia)


class InscricaoTests(Base):
    def test_inscrever_e_cancelar_o_aparelho(self):
        self.client.force_login(self.usuario_ricardo)
        dados = {'endpoint': 'https://fcm.googleapis.com/fcm/send/abc', 'keys': {'p256dh': 'x', 'auth': 'y'}}
        resposta = self.client.post('/avisos/inscricao/', json.dumps(dados), content_type='application/json')
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(InscricaoPush.objects.get().usuario, self.usuario_ricardo)
        self.client.delete('/avisos/inscricao/', json.dumps(dados), content_type='application/json')
        self.assertFalse(InscricaoPush.objects.exists())

    def test_inscricao_exige_login(self):
        resposta = self.client.post('/avisos/inscricao/', '{}', content_type='application/json')
        self.assertEqual(resposta.status_code, 302)

    def test_inscricao_invalida(self):
        self.client.force_login(self.usuario_ricardo)
        resposta = self.client.post('/avisos/inscricao/', '{"endpoint": "http://x"}', content_type='application/json')
        self.assertEqual(resposta.status_code, 400)


class DestinatariosTests(Base):
    def test_barbeiro_com_login_recebe(self):
        ag = Agendamento(barbearia=self.barbearia, barbeiro=self.ricardo)
        self.assertEqual(list(destinatarios(ag)), [self.usuario_ricardo])

    def test_sem_login_quem_recebe_e_o_dono(self):
        paulo = Barbeiro.objects.create(barbearia=self.barbearia, nome='Paulo')
        ag = Agendamento(barbearia=self.barbearia, barbeiro=paulo)
        self.assertEqual(list(destinatarios(ag)), [self.dono])


@override_settings(**CHAVES)
class EnvioAoAgendarTests(Base):
    def setUp(self):
        hoje = timezone.localdate()
        self.dia = hoje + timedelta(days=(3 - hoje.weekday()) % 7 + 7)
        InscricaoPush.objects.create(
            usuario=self.usuario_ricardo, endpoint='https://fcm.googleapis.com/fcm/send/abc', p256dh='x', auth='y'
        )

    def agendar(self):
        return self.client.post(f'/agendar/{self.barbearia.slug}/', {
            'servico': self.servico.pk, 'barbeiro': self.ricardo.pk, 'data': self.dia.isoformat(), 'hora': '10:00',
            'nome': 'Maria Clara', 'telefone': '11912345678',
        })

    @mock.patch('pywebpush.webpush')
    def test_barbeiro_recebe_o_aviso(self, webpush):
        with self.captureOnCommitCallbacks(execute=True):
            self.agendar()
        webpush.assert_called_once()
        mensagem = json.loads(webpush.call_args.kwargs['data'])
        self.assertIn('Maria Clara', mensagem['corpo'])
        self.assertEqual(mensagem['url'], f'/?data={self.dia.isoformat()}')

    @mock.patch('pywebpush.webpush')
    def test_aparelho_desinscrito_e_apagado(self, webpush):
        from pywebpush import WebPushException

        webpush.side_effect = WebPushException('gone', response=mock.Mock(status_code=410))
        with self.captureOnCommitCallbacks(execute=True):
            self.agendar()
        self.assertTrue(Agendamento.objects.exists())  # o agendamento vale mesmo com o aviso falhando
        self.assertFalse(InscricaoPush.objects.exists())

    @mock.patch('pywebpush.webpush', side_effect=RuntimeError('sem internet'))
    def test_falha_no_aviso_nao_impede_o_agendamento(self, webpush):
        with self.captureOnCommitCallbacks(execute=True):
            resposta = self.agendar()
        self.assertEqual(resposta.status_code, 302)
        self.assertTrue(Agendamento.objects.exists())

    @override_settings(VAPID_PRIVATE_KEY='')
    @mock.patch('pywebpush.webpush')
    def test_sem_chaves_nada_e_enviado(self, webpush):
        with self.captureOnCommitCallbacks(execute=True):
            self.agendar()
        webpush.assert_not_called()
