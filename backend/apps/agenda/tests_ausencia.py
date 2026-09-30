"""Ausências de barbeiros: disponibilidade, agenda, página do cliente e agendamento interno."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.test import TestCase
from django.utils import timezone

from apps.cadastros.models import Barbeiro, Bloqueio, Cliente, HorarioTrabalho, Servico
from apps.contas.models import Barbearia, Usuario

from .disponibilidade import ausente_em, dias_de_atendimento, horarios_livres
from .models import Agendamento

SP = ZoneInfo('America/Sao_Paulo')
QUINTA = date(2026, 10, 1)
ANTES = datetime(2026, 9, 30, 12, 0, tzinfo=SP)


def em(dia, hora, minuto=0):
    return datetime.combine(dia, time(hora, minuto), tzinfo=SP)


def proxima_quinta():
    hoje = timezone.localdate()
    return hoje + timedelta(days=(3 - hoje.weekday()) % 7 + 7)


class Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.barbearia = Barbearia.objects.create(nome='Barbearia Teste')
        cls.corte = Servico.objects.create(barbearia=cls.barbearia, nome='Corte', preco=Decimal('40'), duracao_minutos=30)
        cls.ricardo = Barbeiro.objects.create(barbearia=cls.barbearia, nome='Ricardo')
        cls.paulo = Barbeiro.objects.create(barbearia=cls.barbearia, nome='Paulo')
        for barbeiro in (cls.ricardo, cls.paulo):
            for dia in range(7):
                HorarioTrabalho.objects.create(barbeiro=barbeiro, dia_semana=dia, inicio=time(9), fim=time(18))
        cls.joao = Cliente.objects.create(barbearia=cls.barbearia, nome='João Pereira', telefone='11987654321')


class DisponibilidadeComAusenciaTests(Base):
    def livres(self, barbeiro):
        return [h.astimezone(SP).strftime('%H:%M') for h in horarios_livres(barbeiro, self.corte, QUINTA, ANTES)]

    def test_ausencia_de_parte_do_dia(self):
        Bloqueio.objects.create(barbeiro=self.paulo, data_inicio=QUINTA, data_fim=QUINTA, hora_inicio=time(13), hora_fim=time(15))
        livres = self.livres(self.paulo)
        self.assertIn('12:30', livres)
        self.assertNotIn('12:45', livres)  # 12:45-13:15 invadiria a ausência
        self.assertNotIn('14:00', livres)
        self.assertIn('15:00', livres)
        # O dia continua disponível: só uma parte ficou bloqueada.
        self.assertIn(QUINTA, dias_de_atendimento(self.paulo, a_partir_de=QUINTA))

    def test_ausencia_do_dia_inteiro(self):
        Bloqueio.objects.create(barbeiro=self.paulo, data_inicio=QUINTA, data_fim=QUINTA)
        self.assertEqual(self.livres(self.paulo), [])
        self.assertNotIn(QUINTA, dias_de_atendimento(self.paulo, a_partir_de=QUINTA))
        self.assertTrue(self.livres(self.ricardo))  # o outro barbeiro segue atendendo

    def test_ausente_em(self):
        Bloqueio.objects.create(barbeiro=self.paulo, data_inicio=QUINTA, data_fim=QUINTA, hora_inicio=time(13), hora_fim=time(15))
        self.assertTrue(ausente_em(self.paulo, em(QUINTA, 14), em(QUINTA, 14, 30)))
        self.assertTrue(ausente_em(self.paulo, em(QUINTA, 12, 45), em(QUINTA, 13, 15)))
        self.assertFalse(ausente_em(self.paulo, em(QUINTA, 15), em(QUINTA, 15, 30)))

    def test_horario_incompleto_e_recusado(self):
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            Bloqueio(barbeiro=self.paulo, data_inicio=QUINTA, data_fim=QUINTA, hora_inicio=time(13)).full_clean()
        with self.assertRaises(ValidationError):
            Bloqueio(
                barbeiro=self.paulo, data_inicio=QUINTA, data_fim=QUINTA + timedelta(days=1),
                hora_inicio=time(13), hora_fim=time(15),
            ).full_clean()


class PaginaDoClienteTests(Base):
    """Fluxo: serviço -> dia -> barbeiros que atendem naquele dia."""

    def setUp(self):
        self.dia = proxima_quinta()

    def pagina(self, **params):
        query = '&'.join(f'{k}={v}' for k, v in {'servico': self.corte.pk, **params}.items())
        return self.client.get(f'/agendar/{self.barbearia.slug}/?{query}').content.decode()

    def test_mostra_todos_que_atendem_no_dia(self):
        html = self.pagina(data=self.dia.isoformat())
        self.assertIn('Ricardo', html)
        self.assertIn('Paulo', html)

    def test_ausente_nao_aparece_no_dia(self):
        Bloqueio.objects.create(barbeiro=self.paulo, data_inicio=self.dia, data_fim=self.dia, motivo='Falta')
        html = self.pagina(data=self.dia.isoformat())
        self.assertIn('Ricardo', html)
        self.assertNotIn('Paulo', html)

    def test_link_do_barbeiro_filtra_a_pagina(self):
        html = self.pagina(data=self.dia.isoformat(), barbeiro=self.ricardo.pk)
        self.assertIn('Horários de <strong>Ricardo</strong>', html)
        self.assertNotIn('>Paulo<', html)

    def test_nao_agenda_com_barbeiro_ausente(self):
        Bloqueio.objects.create(barbeiro=self.paulo, data_inicio=self.dia, data_fim=self.dia)
        self.client.post(f'/agendar/{self.barbearia.slug}/', {
            'servico': self.corte.pk, 'barbeiro': self.paulo.pk, 'data': self.dia.isoformat(), 'hora': '10:00',
            'nome': 'Maria', 'telefone': '11912345678',
        })
        self.assertFalse(Agendamento.objects.exists())

    def test_agenda_escolhendo_barbeiro_e_horario_no_mesmo_toque(self):
        resposta = self.client.post(f'/agendar/{self.barbearia.slug}/', {
            'servico': self.corte.pk, 'barbeiro': self.paulo.pk, 'data': self.dia.isoformat(), 'hora': '10:00',
            'nome': 'Maria', 'telefone': '11912345678',
        })
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(Agendamento.objects.get().barbeiro, self.paulo)


class AgendaComAusenciaTests(Base):
    def setUp(self):
        self.dono = Usuario.objects.create_user('dono', password='senha-de-teste-123', barbearia=self.barbearia)
        self.client.force_login(self.dono)
        self.hoje = timezone.localdate()

    def test_equipe_do_dia(self):
        Bloqueio.objects.create(barbeiro=self.paulo, data_inicio=self.hoje, data_fim=self.hoje, motivo='Falta')
        html = self.client.get('/').content.decode()
        self.assertIn('Equipe hoje', html)
        self.assertIn('equipe__membro--ausente', html)
        self.assertIn('equipe__membro--atendendo', html)

    def test_marcar_falta_e_desfazer(self):
        resposta = self.client.post(f'/ausencias/barbeiro/{self.paulo.pk}/marcar/', {'data': self.hoje.isoformat()})
        self.assertEqual(resposta.status_code, 302)
        ausencia = self.paulo.bloqueios.get()
        self.assertFalse(ausencia.dia_parcial)
        self.client.post(f'/ausencias/{ausencia.pk}/desfazer/')
        self.assertFalse(self.paulo.bloqueios.exists())

    def test_saiu_agora_bloqueia_so_o_resto_do_dia(self):
        self.client.post(f'/ausencias/barbeiro/{self.paulo.pk}/marcar/', {'data': self.hoje.isoformat(), 'modo': 'agora'})
        ausencia = self.paulo.bloqueios.get()
        self.assertTrue(ausencia.dia_parcial)
        self.assertEqual(ausencia.hora_fim, time(23, 59))

    def test_nao_marca_ausencia_no_passado(self):
        ontem = self.hoje - timedelta(days=1)
        self.client.post(f'/ausencias/barbeiro/{self.paulo.pk}/marcar/', {'data': ontem.isoformat()})
        self.assertFalse(self.paulo.bloqueios.exists())

    def test_barbeiro_so_marca_a_propria_ausencia(self):
        usuario = Usuario.objects.create_user(
            'ricardo', password='senha-de-teste-123', barbearia=self.barbearia, papel=Usuario.Papel.BARBEIRO
        )
        self.ricardo.usuario = usuario
        self.ricardo.save()
        self.client.force_login(usuario)
        resposta = self.client.post(f'/ausencias/barbeiro/{self.paulo.pk}/marcar/', {'data': self.hoje.isoformat()})
        self.assertEqual(resposta.status_code, 404)
        self.assertFalse(self.paulo.bloqueios.exists())

    def test_horario_afetado_fica_destacado_com_aviso_ao_cliente(self):
        amanha = self.hoje + timedelta(days=1)
        Agendamento.objects.create(
            barbearia=self.barbearia, cliente=self.joao, barbeiro=self.paulo, servico=self.corte, inicio=em(amanha, 10)
        )
        resposta = self.client.post(f'/ausencias/barbeiro/{self.paulo.pk}/marcar/', {'data': amanha.isoformat()})
        pagina = self.client.get(resposta['Location'])
        self.assertContains(pagina, '1 horário já marcado com ele está destacado')
        self.assertContains(pagina, 'agendamento--alerta')
        self.assertContains(pagina, 'Avisar cliente no WhatsApp')
        self.assertEqual(Agendamento.objects.get().status, 'agendado')  # nada é cancelado sozinho

    def test_agendamento_interno_pede_confirmacao_com_barbeiro_ausente(self):
        amanha = self.hoje + timedelta(days=1)
        Bloqueio.objects.create(barbeiro=self.paulo, data_inicio=amanha, data_fim=amanha)
        dados = {'cliente': self.joao.pk, 'barbeiro': self.paulo.pk, 'servico': self.corte.pk,
                 'data': amanha.isoformat(), 'hora': '10:00'}
        resposta = self.client.post('/agendamentos/novo/', dados)
        self.assertContains(resposta, 'Paulo está ausente nesse horário')
        self.assertContains(resposta, 'Agendar mesmo assim')
        self.assertFalse(Agendamento.objects.exists())
        self.client.post('/agendamentos/novo/', {**dados, 'agendar_mesmo_assim': 'on'})
        self.assertTrue(Agendamento.objects.exists())
