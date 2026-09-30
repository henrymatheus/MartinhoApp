from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.cadastros.models import Barbeiro, Cliente, Servico
from apps.contas.models import Barbearia

from .models import Agendamento, Atendimento, ItemAtendimento

SP = ZoneInfo('America/Sao_Paulo')


def hora(h, m=0):
    return datetime(2026, 10, 1, h, m, tzinfo=SP)


class BaseAgenda(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.barbearia = Barbearia.objects.create(nome='Barbearia Teste')
        cls.ricardo = Barbeiro.objects.create(barbearia=cls.barbearia, nome='Ricardo')
        cls.paulo = Barbeiro.objects.create(barbearia=cls.barbearia, nome='Paulo')
        cls.corte = Servico.objects.create(
            barbearia=cls.barbearia, nome='Corte de cabelo', preco=Decimal('40.00'), duracao_minutos=30
        )
        cls.joao = Cliente.objects.create(barbearia=cls.barbearia, nome='João Pereira')
        cls.carlos = Cliente.objects.create(barbearia=cls.barbearia, nome='Carlos Mendes')

    def agendamento(self, inicio, barbeiro=None, cliente=None, **extra):
        return Agendamento(
            barbearia=self.barbearia,
            cliente=cliente or self.joao,
            barbeiro=barbeiro or self.ricardo,
            servico=self.corte,
            inicio=inicio,
            **extra,
        )


class ConflitoDeHorarioTests(BaseAgenda):
    def test_fim_e_calculado_pela_duracao_do_servico(self):
        ag = self.agendamento(hora(14))
        ag.save()
        self.assertEqual(ag.fim, hora(14, 30))

    def test_banco_recusa_horarios_sobrepostos_do_mesmo_barbeiro(self):
        self.agendamento(hora(14)).save()
        # save() direto, sem full_clean: simula duas gravações simultâneas que
        # passaram pela validação em Python. Quem barra é o PostgreSQL.
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.agendamento(hora(14, 15), cliente=self.carlos).save()

    def test_full_clean_mostra_mensagem_amigavel(self):
        self.agendamento(hora(14)).save()
        novo = self.agendamento(hora(14, 15), cliente=self.carlos)
        with self.assertRaisesMessage(ValidationError, 'Esse barbeiro já tem um agendamento nesse horário.'):
            novo.full_clean()

    def test_horarios_encostados_nao_conflitam(self):
        self.agendamento(hora(14)).save()
        self.agendamento(hora(14, 30), cliente=self.carlos).save()
        self.assertEqual(Agendamento.objects.count(), 2)

    def test_barbeiros_diferentes_no_mesmo_horario(self):
        self.agendamento(hora(14)).save()
        self.agendamento(hora(14), barbeiro=self.paulo, cliente=self.carlos).save()
        self.assertEqual(Agendamento.objects.count(), 2)

    def test_agendamento_cancelado_libera_o_horario(self):
        self.agendamento(hora(14), status=Agendamento.Status.CANCELADO).save()
        self.agendamento(hora(14), cliente=self.carlos).save()
        self.assertEqual(Agendamento.objects.count(), 2)

    def test_fim_antes_do_inicio_e_recusado(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.agendamento(hora(14), fim=hora(13)).save()


class IsolamentoEntreBarbeariasTests(BaseAgenda):
    def test_cliente_de_outra_barbearia_e_recusado(self):
        outra = Barbearia.objects.create(nome='Outra')
        cliente_de_fora = Cliente.objects.create(barbearia=outra, nome='Cliente de fora')
        ag = self.agendamento(hora(10), cliente=cliente_de_fora)
        with self.assertRaises(ValidationError) as erro:
            ag.full_clean()
        self.assertIn('cliente', erro.exception.message_dict)


class HistoricoTests(BaseAgenda):
    def test_item_copia_nome_e_preco_do_servico(self):
        atendimento = Atendimento.objects.create(barbearia=self.barbearia, cliente=self.joao, barbeiro=self.ricardo)
        item = ItemAtendimento.objects.create(atendimento=atendimento, servico=self.corte)
        self.assertEqual(item.descricao, 'Corte de cabelo')
        self.assertEqual(item.valor, Decimal('40.00'))

    def test_reajuste_de_preco_nao_altera_o_historico(self):
        atendimento = Atendimento.objects.create(barbearia=self.barbearia, cliente=self.joao)
        ItemAtendimento.objects.create(atendimento=atendimento, servico=self.corte)
        self.corte.preco = Decimal('50.00')
        self.corte.save()
        self.assertEqual(atendimento.total, Decimal('40.00'))

    def test_total_soma_os_itens(self):
        atendimento = Atendimento.objects.create(barbearia=self.barbearia, cliente=self.joao)
        ItemAtendimento.objects.create(atendimento=atendimento, servico=self.corte)
        ItemAtendimento.objects.create(atendimento=atendimento, descricao='Barba', valor=Decimal('25.50'))
        self.assertEqual(atendimento.total, Decimal('65.50'))
