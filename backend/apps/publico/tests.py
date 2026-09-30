from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.agenda.disponibilidade import dias_de_atendimento, horarios_livres
from apps.agenda.models import Agendamento
from apps.cadastros.models import Barbeiro, Bloqueio, Cliente, HorarioTrabalho, Servico
from apps.contas.models import Barbearia

SP = ZoneInfo('America/Sao_Paulo')
# Uma quinta-feira fixa (weekday 3), para os testes não dependerem do dia de hoje.
QUINTA = date(2026, 10, 1)
AGORA = datetime(2026, 9, 30, 12, 0, tzinfo=SP)


def proxima_quinta():
    """A quinta-feira da semana que vem: sempre no futuro e dentro dos 30 dias."""
    hoje = timezone.localdate()
    return hoje + timedelta(days=(3 - hoje.weekday()) % 7 + 7)


def em(dia, hora, minuto=0):
    return datetime.combine(dia, time(hora, minuto), tzinfo=SP)


class Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.barbearia = Barbearia.objects.create(nome='Barbearia do João', telefone='(11) 93456-7890')
        cls.ricardo = Barbeiro.objects.create(barbearia=cls.barbearia, nome='Ricardo')
        cls.corte = Servico.objects.create(barbearia=cls.barbearia, nome='Corte', preco=Decimal('40'), duracao_minutos=30)
        # Quinta: 09:00-12:00 e 13:00-15:00 (almoço 12-13).
        HorarioTrabalho.objects.create(barbeiro=cls.ricardo, dia_semana=3, inicio=time(9), fim=time(12))
        HorarioTrabalho.objects.create(barbeiro=cls.ricardo, dia_semana=3, inicio=time(13), fim=time(15))

    def livres(self, dia=QUINTA, agora=AGORA):
        return [h.astimezone(SP).strftime('%H:%M') for h in horarios_livres(self.ricardo, self.corte, dia, agora)]


class DisponibilidadeTests(Base):
    def test_horarios_dentro_do_expediente_e_fora_do_almoco(self):
        livres = self.livres()
        self.assertEqual(livres[0], '09:00')
        self.assertIn('11:30', livres)  # 11:30-12:00 cabe
        self.assertNotIn('11:45', livres)  # 11:45-12:15 invadiria o almoço
        self.assertNotIn('12:00', livres)
        self.assertIn('13:00', livres)
        self.assertEqual(livres[-1], '14:30')

    def test_agendamento_existente_ocupa_o_horario(self):
        Agendamento.objects.create(
            barbearia=self.barbearia, cliente=Cliente.objects.create(barbearia=self.barbearia, nome='A'),
            barbeiro=self.ricardo, servico=self.corte, inicio=em(QUINTA, 10),
        )
        livres = self.livres()
        self.assertNotIn('09:45', livres)  # 09:45-10:15 bateria nas 10:00
        self.assertNotIn('10:00', livres)
        self.assertNotIn('10:15', livres)
        self.assertIn('09:30', livres)
        self.assertIn('10:30', livres)

    def test_cancelado_nao_ocupa(self):
        Agendamento.objects.create(
            barbearia=self.barbearia, cliente=Cliente.objects.create(barbearia=self.barbearia, nome='A'),
            barbeiro=self.ricardo, servico=self.corte, inicio=em(QUINTA, 10), status='cancelado',
        )
        self.assertIn('10:00', self.livres())

    def test_folga_zera_o_dia(self):
        Bloqueio.objects.create(barbeiro=self.ricardo, data_inicio=QUINTA, data_fim=QUINTA)
        self.assertEqual(self.livres(), [])
        self.assertNotIn(QUINTA, dias_de_atendimento(self.ricardo, a_partir_de=QUINTA - timedelta(days=1)))

    def test_antecedencia_minima_de_uma_hora(self):
        livres = self.livres(agora=em(QUINTA, 9, 50))
        self.assertNotIn('10:30', livres)
        self.assertEqual(livres[0], '11:00')

    def test_dia_sem_turno(self):
        self.assertEqual(self.livres(dia=QUINTA + timedelta(days=1)), [])


class AgendamentoPeloClienteTests(Base):
    # Aqui o relógio é o real: o agendamento é feito na próxima quinta.
    def setUp(self):
        self.quinta = proxima_quinta()
    def url(self, **params):
        base = reverse('publico:agendar', args=[self.barbearia.slug])
        return base + ('?' + '&'.join(f'{k}={v}' for k, v in params.items()) if params else '')

    def dados(self, **extra):
        dados = {
            'servico': self.corte.pk, 'barbeiro': self.ricardo.pk, 'data': self.quinta.isoformat(), 'hora': '10:00',
            'nome': 'Maria Clara', 'telefone': '(11) 91234-5678',
        }
        dados.update(extra)
        return dados

    def test_endereco_gerado_pelo_nome(self):
        self.assertEqual(self.barbearia.slug, 'barbearia-do-joao')

    def test_passos_aparecem_conforme_as_escolhas(self):
        self.assertContains(self.client.get(self.url()), 'Corte')
        resposta = self.client.get(self.url(servico=self.corte.pk, barbeiro=self.ricardo.pk, data=self.quinta.isoformat()))
        self.assertContains(resposta, '09:00')
        self.assertContains(resposta, '14:30')

    def test_agendar_cria_cliente_e_agendamento(self):
        resposta = self.client.post(self.url(), self.dados())
        self.assertEqual(resposta.status_code, 302)
        ag = Agendamento.objects.get()
        self.assertEqual((ag.cliente.nome, ag.inicio, ag.status), ('Maria Clara', em(self.quinta, 10), 'agendado'))
        confirmacao = self.client.get(resposta['Location'])
        self.assertContains(confirmacao, 'Horário confirmado')
        self.assertContains(confirmacao, 'wa.me/5511934567890')

    def test_cliente_existente_e_reconhecido_pelo_telefone(self):
        existente = Cliente.objects.create(barbearia=self.barbearia, nome='Maria C. Souza', telefone='11912345678')
        self.client.post(self.url(), self.dados(telefone='+55 (11) 91234-5678', nome='Maria'))
        self.assertEqual(Agendamento.objects.get().cliente, existente)
        self.assertEqual(Cliente.objects.count(), 1)

    def test_horario_ocupado_nao_agenda(self):
        self.client.post(self.url(), self.dados())
        resposta = self.client.post(self.url(), self.dados(nome='Outra Pessoa', telefone='(11) 95555-4444'))
        self.assertContains(resposta, 'não está mais disponível')
        self.assertEqual(Agendamento.objects.count(), 1)

    def test_horario_fora_do_expediente_nao_agenda(self):
        self.client.post(self.url(), self.dados(hora='12:15'))
        self.assertFalse(Agendamento.objects.exists())

    def test_telefone_invalido(self):
        resposta = self.client.post(self.url(), self.dados(telefone='1234'))
        self.assertContains(resposta, 'Confira o número')
        self.assertFalse(Agendamento.objects.exists())

    def test_limite_de_horarios_por_telefone(self):
        for hora in ('09:00', '09:30', '10:00'):
            self.client.post(self.url(), self.dados(hora=hora))
        resposta = self.client.post(self.url(), self.dados(hora='11:00'))
        self.assertContains(resposta, 'já tem 3 horários marcados')
        self.assertEqual(Agendamento.objects.count(), 3)

    def test_robo_e_ignorado(self):
        self.client.post(self.url(), self.dados(site='http://spam'))
        self.assertFalse(Agendamento.objects.exists())

    def test_agendamento_online_desligado(self):
        Barbearia.objects.filter(pk=self.barbearia.pk).update(agendamento_online=False)
        self.assertEqual(self.client.get(self.url()).status_code, 404)

    def test_confirmacao_com_codigo_adulterado(self):
        url = reverse('publico:confirmado', args=[self.barbearia.slug, '1:abc'])
        self.assertEqual(self.client.get(url).status_code, 404)


class PwaTests(Base):
    def test_manifestos_e_service_worker(self):
        self.assertContains(self.client.get('/manifest.webmanifest'), '"start_url": "/"')
        self.assertContains(
            self.client.get(f'/agendar/{self.barbearia.slug}/manifest.webmanifest'), f'/agendar/{self.barbearia.slug}/'
        )
        resposta = self.client.get('/sw.js')
        self.assertEqual(resposta['Content-Type'], 'application/javascript')
        self.assertContains(resposta, 'offline')
