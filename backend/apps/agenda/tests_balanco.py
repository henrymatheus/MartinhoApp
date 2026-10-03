from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.test import TestCase
from django.utils import timezone

from apps.cadastros.models import Barbeiro, Cliente, Servico
from apps.contas.models import Barbearia, Usuario

from .balanco import Periodo, calcular
from .models import Agendamento, Atendimento, ItemAtendimento

SP = ZoneInfo('America/Sao_Paulo')
QUINTA = date(2026, 10, 1)


class PeriodoTests(TestCase):
    def test_semana_vai_de_segunda_a_domingo(self):
        p = Periodo.do_tipo('semana', QUINTA)
        self.assertEqual((p.inicio, p.fim), (date(2026, 9, 28), date(2026, 10, 4)))

    def test_mes_anterior_e_seguinte(self):
        fevereiro = Periodo.do_tipo('mes', date(2026, 2, 10))
        self.assertEqual(fevereiro.fim, date(2026, 2, 28))
        self.assertEqual(fevereiro.deslocar(-1).inicio, date(2026, 1, 1))
        self.assertEqual(fevereiro.deslocar(1).fim, date(2026, 3, 31))

    def test_parametro_invalido_cai_na_semana_atual(self):
        p = Periodo.da_requisicao({'periodo': 'xyz', 'data': 'ontem'}, QUINTA)
        self.assertEqual(p, Periodo.do_tipo('semana', QUINTA))

    def test_datas_livres_invertidas_sao_corrigidas(self):
        p = Periodo.da_requisicao({'periodo': 'livre', 'de': '2026-10-10', 'ate': '2026-10-01'}, QUINTA)
        self.assertEqual((p.inicio, p.fim), (date(2026, 10, 1), date(2026, 10, 10)))

    def test_faixa_livre_muito_longa_e_cortada(self):
        p = Periodo.da_requisicao({'periodo': 'livre', 'de': '2020-01-01', 'ate': '2026-01-01'}, QUINTA)
        self.assertEqual(p.dias, 366)

    def test_semana_em_andamento_compara_ate_o_mesmo_dia(self):
        # Quinta desta semana: compara com segunda a quinta da semana passada.
        anterior = Periodo.do_tipo('semana', QUINTA).para_comparar(QUINTA)
        self.assertEqual((anterior.inicio, anterior.fim), (date(2026, 9, 21), date(2026, 9, 24)))

    def test_semana_encerrada_compara_com_a_semana_inteira(self):
        anterior = Periodo.do_tipo('semana', date(2026, 9, 22)).para_comparar(QUINTA)
        self.assertEqual((anterior.inicio, anterior.fim), (date(2026, 9, 14), date(2026, 9, 20)))


class BaseBalanco(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.barbearia = Barbearia.objects.create(nome='Barbearia Teste')
        cls.ricardo = Barbeiro.objects.create(barbearia=cls.barbearia, nome='Ricardo')
        cls.paulo = Barbeiro.objects.create(barbearia=cls.barbearia, nome='Paulo')
        cls.corte = Servico.objects.create(barbearia=cls.barbearia, nome='Corte', preco=Decimal('40.00'))
        cls.barba = Servico.objects.create(barbearia=cls.barbearia, nome='Barba', preco=Decimal('25.00'))
        cls.joao = Cliente.objects.create(barbearia=cls.barbearia, nome='João Pereira', telefone='(11) 98765-4321')
        cls.carlos = Cliente.objects.create(barbearia=cls.barbearia, nome='Carlos Mendes')
        cls.dono = Usuario.objects.create_user('dono', password='senha-de-teste-123', barbearia=cls.barbearia)
        cls.usuario_ricardo = Usuario.objects.create_user(
            'ricardo', password='senha-de-teste-123', barbearia=cls.barbearia, papel=Usuario.Papel.BARBEIRO
        )
        cls.ricardo.usuario = cls.usuario_ricardo
        cls.ricardo.save()

    def atendimento(self, dia, barbeiro, cliente, *servicos):
        at = Atendimento.objects.create(barbearia=self.barbearia, cliente=cliente, barbeiro=barbeiro, data=dia)
        for servico in servicos:
            ItemAtendimento.objects.create(atendimento=at, servico=servico)
        return at

    def semana(self):
        return Periodo.do_tipo('semana', QUINTA)


class CalculoTests(BaseBalanco):
    def test_contagens_do_periodo(self):
        self.atendimento(QUINTA, self.ricardo, self.joao, self.corte, self.barba)
        self.atendimento(QUINTA, self.ricardo, self.joao)
        self.atendimento(date(2026, 9, 29), self.ricardo, self.carlos)
        self.atendimento(date(2026, 9, 20), self.ricardo, self.carlos)  # semana anterior
        r = calcular(self.barbearia, self.semana(), QUINTA)
        # Corte + barba no mesmo atendimento contam como um atendimento só.
        self.assertEqual(r['quantidade'], 3)
        self.assertEqual(r['clientes'], 2)
        # Segunda a quinta já passaram: 3 atendimentos em 4 dias.
        self.assertEqual(r['media_por_dia'], 0.8)
        self.assertEqual([(d['data'], d['quantidade']) for d in r['dias']], [(QUINTA, 2), (date(2026, 9, 29), 1)])

    def test_grafico_tem_uma_barra_por_dia(self):
        self.atendimento(QUINTA, self.ricardo, self.joao)
        self.atendimento(QUINTA, self.ricardo, self.carlos)
        self.atendimento(date(2026, 9, 29), self.ricardo, self.carlos)
        g = calcular(self.barbearia, self.semana(), QUINTA)['grafico']
        self.assertEqual([b['quantidade'] for b in g['barras']], [0, 1, 0, 2, 0, 0, 0])
        self.assertEqual([b['altura'] for b in g['barras']][:4], [0, 50, 0, 100])
        self.assertEqual([b['futuro'] for b in g['barras']], [False] * 4 + [True] * 3)
        self.assertEqual(g['maior'], 2)

    def test_faixa_longa_tem_uma_barra_por_mes(self):
        self.atendimento(date(2026, 8, 5), self.ricardo, self.joao)
        periodo = Periodo('livre', date(2026, 7, 15), date(2026, 9, 30))
        g = calcular(self.barbearia, periodo, QUINTA)['grafico']
        self.assertEqual((g['tipo'], [b['quantidade'] for b in g['barras']]), ('mes', [0, 1, 0]))

    def test_um_dia_nao_tem_grafico(self):
        self.assertIsNone(calcular(self.barbearia, Periodo.do_tipo('dia', QUINTA), QUINTA)['grafico'])

    def test_filtra_por_barbeiro_e_agrupa_por_barbeiro(self):
        self.atendimento(QUINTA, self.ricardo, self.joao)
        self.atendimento(QUINTA, self.paulo, self.carlos)
        self.atendimento(QUINTA, self.paulo, self.joao)
        self.assertEqual(calcular(self.barbearia, self.semana(), QUINTA, self.ricardo)['quantidade'], 1)
        todos = calcular(self.barbearia, self.semana(), QUINTA)
        self.assertEqual([(b['barbeiro__nome'], b['quantidade']) for b in todos['por_barbeiro']], [('Paulo', 2), ('Ricardo', 1)])

    def test_faltas_e_cancelamentos_nao_contam_como_atendimento(self):
        for h, status in ((9, Agendamento.Status.FALTOU), (10, Agendamento.Status.CANCELADO)):
            Agendamento.objects.create(
                barbearia=self.barbearia, cliente=self.joao, barbeiro=self.ricardo, servico=self.corte,
                inicio=datetime(2026, 10, 1, h, tzinfo=SP), status=status,
            )
        r = calcular(self.barbearia, self.semana(), QUINTA)
        self.assertEqual((r['faltas'], r['cancelados'], r['quantidade']), (1, 1, 0))

    def test_comparacao_com_o_periodo_anterior(self):
        self.atendimento(date(2026, 9, 22), self.ricardo, self.joao)  # terça passada
        self.atendimento(date(2026, 9, 23), self.ricardo, self.joao)  # quarta passada
        self.atendimento(date(2026, 9, 26), self.ricardo, self.joao)  # sábado passado: fora do corte
        self.atendimento(QUINTA, self.ricardo, self.joao)
        self.atendimento(QUINTA, self.ricardo, self.carlos)
        self.atendimento(QUINTA, self.paulo, self.carlos)
        comparacao = calcular(self.barbearia, self.semana(), QUINTA)['comparacao']
        self.assertEqual((comparacao['quantidade'], comparacao['variacao'], comparacao['parcial']), (2, 50, True))

    def test_faturamento_ticket_medio_e_volume_por_servico(self):
        self.atendimento(QUINTA, self.ricardo, self.joao, self.corte, self.barba)  # 65
        self.atendimento(QUINTA, self.paulo, self.carlos, self.corte)  # 40
        self.atendimento(QUINTA, self.paulo, self.carlos)  # sem serviço: R$ 0
        r = calcular(self.barbearia, self.semana(), QUINTA)
        self.assertEqual(r['faturamento'], Decimal('105.00'))
        self.assertEqual(r['ticket_medio'], Decimal('35.00'))
        self.assertEqual(
            [(s['descricao'], s['quantidade'], s['valor']) for s in r['por_servico']],
            [('Corte', 2, Decimal('80.00')), ('Barba', 1, Decimal('25.00'))],
        )
        # Corte + barba no mesmo atendimento: um atendimento só, com os dois valores.
        self.assertEqual(
            [(b['barbeiro__nome'], b['quantidade'], b['valor']) for b in r['por_barbeiro']],
            [('Paulo', 2, Decimal('40.00')), ('Ricardo', 1, Decimal('65.00'))],
        )
        self.assertEqual(r['dias'][0]['valor'], Decimal('105.00'))

    def test_reajuste_de_preco_nao_muda_o_faturamento_passado(self):
        self.atendimento(QUINTA, self.ricardo, self.joao, self.corte)
        Servico.objects.filter(pk=self.corte.pk).update(preco=Decimal('60.00'))
        self.assertEqual(calcular(self.barbearia, self.semana(), QUINTA)['faturamento'], Decimal('40.00'))

    def test_comparacao_do_faturamento(self):
        self.atendimento(date(2026, 9, 22), self.ricardo, self.joao, self.corte)  # semana passada: 40
        self.atendimento(QUINTA, self.ricardo, self.joao, self.corte, self.barba)  # esta semana: 65
        comparacao = calcular(self.barbearia, self.semana(), QUINTA)['comparacao']
        self.assertEqual((comparacao['faturamento'], comparacao['variacao_faturamento']), (Decimal('40.00'), 62))

    def test_nao_mistura_barbearias(self):
        outra = Barbearia.objects.create(nome='Outra')
        Atendimento.objects.create(
            barbearia=outra, cliente=Cliente.objects.create(barbearia=outra, nome='De fora'), data=QUINTA
        )
        self.assertEqual(calcular(self.barbearia, self.semana(), QUINTA)['quantidade'], 0)


class TelaBalancoTests(BaseBalanco):
    URL = '/historico/?periodo=semana&data=2026-10-01'

    def setUp(self):
        self.atendimento(QUINTA, self.ricardo, self.joao, self.corte)
        self.atendimento(QUINTA, self.paulo, self.carlos, self.barba)

    def test_sem_login_vai_para_a_tela_de_entrar(self):
        resposta = self.client.get('/historico/')
        self.assertEqual(resposta.status_code, 302)

    def test_abre_na_semana_atual(self):
        self.client.force_login(self.dono)
        resposta = self.client.get('/historico/')
        self.assertEqual(resposta.context['periodo'], Periodo.do_tipo('semana', timezone.localdate()))

    def test_dono_ve_todos_e_pode_filtrar(self):
        self.client.force_login(self.dono)
        resposta = self.client.get(self.URL)
        self.assertContains(resposta, 'João Pereira')
        self.assertContains(resposta, 'Carlos Mendes')
        self.assertContains(resposta, 'Por barbeiro')
        resposta = self.client.get(f'{self.URL}&barbeiro={self.paulo.pk}')
        self.assertNotContains(resposta, 'João Pereira')
        self.assertContains(resposta, 'Carlos Mendes')

    def test_mostra_faturamento_e_servicos(self):
        self.client.force_login(self.dono)
        resposta = self.client.get(self.URL)
        self.assertContains(resposta, 'Histórico de atendimentos')
        self.assertContains(resposta, 'R$ 65,00')  # corte 40 + barba 25
        self.assertContains(resposta, 'Serviços')

    def test_endereco_antigo_do_balanco_redireciona(self):
        self.client.force_login(self.dono)
        resposta = self.client.get('/balanco/?periodo=semana&data=2026-10-01')
        self.assertRedirects(resposta, self.URL)

    def test_barbeiro_ve_so_o_proprio_mesmo_trocando_a_url(self):
        self.client.force_login(self.usuario_ricardo)
        resposta = self.client.get(f'{self.URL}&barbeiro={self.paulo.pk}')
        self.assertContains(resposta, 'Meu histórico')
        self.assertContains(resposta, 'João Pereira')
        self.assertNotContains(resposta, 'Carlos Mendes')
        self.assertNotContains(resposta, 'Por barbeiro')

    def test_barbeiro_sem_vinculo_nao_ve_valores(self):
        solto = Usuario.objects.create_user(
            'novato', password='senha-de-teste-123', barbearia=self.barbearia, papel=Usuario.Papel.BARBEIRO
        )
        self.client.force_login(solto)
        resposta = self.client.get(self.URL)
        self.assertContains(resposta, 'ainda não está ligado a um barbeiro')
        self.assertNotContains(resposta, 'João Pereira')
        self.assertEqual(self.client.get('/historico/exportar/').status_code, 404)

    def test_barbeiro_de_outra_barbearia_da_404(self):
        outra = Barbearia.objects.create(nome='Outra')
        de_fora = Barbeiro.objects.create(barbearia=outra, nome='De fora')
        self.client.force_login(self.dono)
        self.assertEqual(self.client.get(f'{self.URL}&barbeiro={de_fora.pk}').status_code, 404)

    def test_csv_do_periodo(self):
        Cliente.objects.filter(pk=self.carlos.pk).update(nome='=HIPERLINK("x")')
        self.client.force_login(self.dono)
        resposta = self.client.get('/historico/exportar/?periodo=semana&data=2026-10-01')
        conteudo = resposta.content.decode('utf-8-sig')
        self.assertIn('01/10/2026;sem horário;João Pereira;Ricardo;Corte;40,00;', conteudo)
        self.assertNotIn('R$', conteudo)
        # O nome começado por "=" não vira fórmula no Excel.
        self.assertIn(';"\'=HIPERLINK(""x"")";', conteudo)

    def test_csv_do_barbeiro_so_tem_os_dele(self):
        self.client.force_login(self.usuario_ricardo)
        conteudo = self.client.get('/historico/exportar/?periodo=semana&data=2026-10-01').content.decode('utf-8-sig')
        self.assertIn('João Pereira', conteudo)
        self.assertNotIn('Carlos Mendes', conteudo)


class RegistrarAtendimentoTests(BaseBalanco):
    URL = '/atendimentos/novo/'

    def dados(self, **extra):
        return {'barbeiro': self.ricardo.pk, 'data': timezone.localdate().isoformat(), 'servicos': [self.corte.pk], **extra}

    def test_registra_atendimento(self):
        self.client.force_login(self.dono)
        resposta = self.client.post(self.URL, self.dados(cliente=self.joao.pk))
        at = Atendimento.objects.get()
        self.assertEqual((at.cliente, at.barbeiro, at.agendamento), (self.joao, self.ricardo, None))
        # O serviço marcado vira item, com o preço copiado do cadastro.
        self.assertEqual([(i.descricao, i.valor) for i in at.itens.all()], [('Corte', Decimal('40.00'))])
        self.assertRedirects(resposta, f'/historico/?periodo=dia&data={at.data.isoformat()}&barbeiro={self.ricardo.pk}')

    def test_varios_servicos_e_servico_obrigatorio(self):
        self.client.force_login(self.dono)
        self.client.post(self.URL, self.dados(cliente=self.joao.pk, servicos=[self.corte.pk, self.barba.pk]))
        self.assertEqual(Atendimento.objects.get().total, Decimal('65.00'))
        resposta = self.client.post(self.URL, self.dados(cliente=self.joao.pk, servicos=[]))
        self.assertContains(resposta, 'Marque pelo menos um serviço')
        self.assertEqual(Atendimento.objects.count(), 1)

    def test_cliente_novo_com_telefone_ja_cadastrado_vai_para_a_ficha_existente(self):
        self.client.force_login(self.dono)
        self.client.post(self.URL, self.dados(novo_nome='Joãozinho', novo_telefone='11987654321'))
        self.assertEqual(Atendimento.objects.get().cliente, self.joao)
        self.assertEqual(Cliente.objects.count(), 2)

    def test_cliente_novo_sem_telefone_e_cadastrado(self):
        self.client.force_login(self.dono)
        self.client.post(self.URL, self.dados(novo_nome='Visitante'))
        self.assertEqual(Atendimento.objects.get().cliente.nome, 'Visitante')

    def test_exige_cliente(self):
        self.client.force_login(self.dono)
        resposta = self.client.post(self.URL, self.dados())
        self.assertContains(resposta, 'Escolha um cliente da lista')
        self.assertFalse(Atendimento.objects.exists())

    def test_recusa_data_futura(self):
        self.client.force_login(self.dono)
        resposta = self.client.post(self.URL, self.dados(cliente=self.joao.pk, data='2099-01-01'))
        self.assertContains(resposta, 'data futura')
        self.assertFalse(Atendimento.objects.exists())

    def test_barbeiro_registra_so_para_si(self):
        self.client.force_login(self.usuario_ricardo)
        resposta = self.client.post(self.URL, self.dados(cliente=self.joao.pk, barbeiro=self.paulo.pk))
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(Atendimento.objects.exists())
        self.client.post(self.URL, self.dados(cliente=self.joao.pk))
        self.assertEqual(Atendimento.objects.get().barbeiro, self.ricardo)
