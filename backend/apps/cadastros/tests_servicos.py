from decimal import Decimal

from django.test import TestCase

from apps.contas.models import Barbearia, Usuario

from .models import Servico


class ServicosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.minha = Barbearia.objects.create(nome='Minha')
        cls.outra = Barbearia.objects.create(nome='Outra')
        cls.corte = Servico.objects.create(barbearia=cls.minha, nome='Corte', preco=Decimal('40.00'))
        cls.de_fora = Servico.objects.create(barbearia=cls.outra, nome='Serviço de fora', preco=Decimal('10.00'))
        cls.dono = Usuario.objects.create_user('dono', password='senha-de-teste-123', barbearia=cls.minha)
        cls.barbeiro = Usuario.objects.create_user(
            'barbeiro', password='senha-de-teste-123', barbearia=cls.minha, papel=Usuario.Papel.BARBEIRO
        )

    def dados(self, **extra):
        dados = {'nome': 'Barba', 'preco': '35,50', 'duracao_minutos': '30', 'ativo': 'on'}
        dados.update(extra)
        return dados

    def test_dono_ve_so_os_servicos_da_propria_barbearia(self):
        self.client.force_login(self.dono)
        resposta = self.client.get('/servicos/')
        self.assertContains(resposta, 'Corte')
        self.assertNotContains(resposta, 'Serviço de fora')

    def test_dono_cadastra_com_preco_no_formato_brasileiro(self):
        self.client.force_login(self.dono)
        self.client.post('/servicos/novo/', self.dados())
        barba = Servico.objects.get(nome='Barba')
        self.assertEqual((barba.barbearia, barba.preco), (self.minha, Decimal('35.50')))

    def test_dono_reajusta_preco_e_desativa(self):
        self.client.force_login(self.dono)
        self.client.post(f'/servicos/{self.corte.pk}/editar/', self.dados(nome='Corte', preco='45,00', ativo=''))
        self.corte.refresh_from_db()
        self.assertEqual((self.corte.preco, self.corte.ativo), (Decimal('45.00'), False))

    def test_nome_repetido_e_recusado(self):
        self.client.force_login(self.dono)
        resposta = self.client.post('/servicos/novo/', self.dados(nome='corte'))
        self.assertContains(resposta, 'Já existe um serviço com esse nome.')

    def test_nome_igual_ao_de_outra_barbearia_e_aceito(self):
        self.client.force_login(self.dono)
        self.client.post('/servicos/novo/', self.dados(nome='Serviço de fora'))
        self.assertTrue(Servico.objects.filter(barbearia=self.minha, nome='Serviço de fora').exists())

    def test_servico_de_outra_barbearia_nao_abre(self):
        self.client.force_login(self.dono)
        self.assertEqual(self.client.get(f'/servicos/{self.de_fora.pk}/editar/').status_code, 404)

    def test_barbeiro_e_barrado_mesmo_digitando_o_endereco(self):
        self.client.force_login(self.barbeiro)
        self.assertEqual(self.client.get('/servicos/').status_code, 403)
        self.assertEqual(self.client.post('/servicos/novo/', self.dados()).status_code, 403)
        self.assertEqual(self.client.post(f'/servicos/{self.corte.pk}/editar/', self.dados(preco='1,00')).status_code, 403)
        self.corte.refresh_from_db()
        self.assertEqual(self.corte.preco, Decimal('40.00'))

    def test_menu_mostra_servicos_so_para_o_dono(self):
        self.client.force_login(self.dono)
        self.assertContains(self.client.get('/clientes/'), 'href="/servicos/"')
        self.client.force_login(self.barbeiro)
        self.assertNotContains(self.client.get('/clientes/'), 'href="/servicos/"')
