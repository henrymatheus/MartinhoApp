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

    def test_save_recusa_horarios_sobrepostos_do_mesmo_barbeiro(self):
        self.agendamento(hora(14)).save()
        # save() direto, sem full_clean: a regra vale em qualquer caminho
        # (API, shell, scripts), não só no admin.
        with self.assertRaisesMessage(ValidationError, 'Esse barbeiro já tem um agendamento nesse horário.'):
            self.agendamento(hora(14, 15), cliente=self.carlos).save()
        self.assertEqual(Agendamento.objects.count(), 1)

    def test_editar_o_proprio_agendamento_nao_conflita_com_ele_mesmo(self):
        ag = self.agendamento(hora(14))
        ag.save()
        ag.observacoes = 'Prefere máquina 2'
        ag.save()
        self.assertEqual(Agendamento.objects.get().observacoes, 'Prefere máquina 2')

    def test_novo_agendamento_que_engloba_outro_conflita(self):
        self.agendamento(hora(14, 10)).save()
        longo = self.agendamento(hora(14), cliente=self.carlos, fim=hora(15))
        with self.assertRaises(ValidationError):
            longo.save()

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


class TelasDaAgendaTests(BaseAgenda):
    def setUp(self):
        from apps.contas.models import Usuario

        self.usuario = Usuario.objects.create_user('dono', password='senha-de-teste-123', barbearia=self.barbearia)
        self.client.force_login(self.usuario)

    def test_sem_login_vai_para_a_tela_de_entrar(self):
        self.client.logout()
        resposta = self.client.get('/')
        self.assertRedirects(resposta, '/entrar/?next=/')

    def test_usuario_sem_barbearia_ve_aviso(self):
        from apps.contas.models import Usuario

        self.client.force_login(Usuario.objects.create_user('solto', password='senha-de-teste-123'))
        resposta = self.client.get('/')
        self.assertContains(resposta, 'não está ligado a uma barbearia', status_code=403)

    def test_agenda_mostra_so_a_propria_barbearia(self):
        self.agendamento(hora(14)).save()
        outra = Barbearia.objects.create(nome='Outra')
        Agendamento.objects.create(
            barbearia=outra,
            cliente=Cliente.objects.create(barbearia=outra, nome='Cliente de fora'),
            barbeiro=Barbeiro.objects.create(barbearia=outra, nome='Barbeiro de fora'),
            servico=Servico.objects.create(barbearia=outra, nome='Corte', preco=10),
            inicio=hora(14),
        )
        resposta = self.client.get('/?data=2026-10-01')
        self.assertContains(resposta, 'João Pereira')
        self.assertNotContains(resposta, 'Cliente de fora')

    def test_dia_vazio_mostra_proximos_horarios(self):
        from django.utils import timezone

        futuro = timezone.localtime() + timedelta(days=3)
        futuro = futuro.replace(hour=10, minute=0, second=0, microsecond=0)
        self.agendamento(futuro).save()
        resposta = self.client.get('/?data=2020-01-01')
        self.assertContains(resposta, 'Próximos horários marcados')
        self.assertContains(resposta, f'?data={futuro.date().isoformat()}')

    def dados_formulario(self, **extra):
        dados = {
            'cliente': self.carlos.pk,
            'barbeiro': self.ricardo.pk,
            'servico': self.corte.pk,
            'data': '2026-10-01',
            'hora': '14:15',
        }
        dados.update(extra)
        return dados

    def test_novo_agendamento(self):
        resposta = self.client.post('/agendamentos/novo/', self.dados_formulario())
        self.assertRedirects(resposta, '/?data=2026-10-01')
        ag = Agendamento.objects.get()
        self.assertEqual(ag.inicio, hora(14, 15))
        self.assertEqual(ag.barbearia, self.barbearia)

    def test_novo_agendamento_em_conflito_mostra_mensagem(self):
        self.agendamento(hora(14)).save()
        resposta = self.client.post('/agendamentos/novo/', self.dados_formulario())
        self.assertContains(resposta, 'Esse barbeiro já tem um agendamento nesse horário.')
        self.assertEqual(Agendamento.objects.count(), 1)

    def test_remarcar_recalcula_o_fim(self):
        ag = self.agendamento(hora(14))
        ag.save()
        self.client.post(f'/agendamentos/{ag.pk}/editar/', self.dados_formulario(cliente=self.joao.pk, hora='16:00'))
        ag.refresh_from_db()
        self.assertEqual((ag.inicio, ag.fim), (hora(16), hora(16, 30)))

    def test_concluir_registra_no_historico(self):
        ag = self.agendamento(hora(14))
        ag.save()
        self.client.post(f'/agendamentos/{ag.pk}/concluir/')
        ag.refresh_from_db()
        self.assertEqual(ag.status, Agendamento.Status.CONCLUIDO)
        atendimento = ag.atendimento
        self.assertEqual((atendimento.cliente, atendimento.total), (self.joao, Decimal('40.00')))

    def test_nao_conclui_duas_vezes(self):
        ag = self.agendamento(hora(14))
        ag.save()
        self.client.post(f'/agendamentos/{ag.pk}/concluir/')
        self.client.post(f'/agendamentos/{ag.pk}/concluir/')
        self.assertEqual(Atendimento.objects.count(), 1)

    def test_nao_mexe_em_agendamento_de_outra_barbearia(self):
        outra = Barbearia.objects.create(nome='Outra')
        ag = Agendamento.objects.create(
            barbearia=outra,
            cliente=Cliente.objects.create(barbearia=outra, nome='X'),
            barbeiro=Barbeiro.objects.create(barbearia=outra, nome='Y'),
            servico=Servico.objects.create(barbearia=outra, nome='Z', preco=10),
            inicio=hora(14),
        )
        resposta = self.client.post(f'/agendamentos/{ag.pk}/cancelar/')
        self.assertEqual(resposta.status_code, 404)


class WhatsappTests(BaseAgenda):
    def test_link_com_codigo_do_brasil_e_mensagem(self):
        self.joao.telefone = '(11) 98765-4321'
        self.assertEqual(self.joao.link_whatsapp('Olá'), 'https://wa.me/5511987654321?text=Ol%C3%A1')

    def test_sem_telefone_nao_gera_link(self):
        self.assertEqual(self.joao.link_whatsapp(), '')
