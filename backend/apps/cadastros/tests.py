from django.test import TestCase

from apps.contas.models import Barbearia, Usuario

from .models import Cliente


class TelasDeClientesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.minha = Barbearia.objects.create(nome='Minha')
        cls.outra = Barbearia.objects.create(nome='Outra')
        cls.joao = Cliente.objects.create(barbearia=cls.minha, nome='João Pereira', telefone='11987654321')
        cls.de_fora = Cliente.objects.create(barbearia=cls.outra, nome='Cliente de fora')
        cls.usuario = Usuario.objects.create_user('dono', password='senha-de-teste-123', barbearia=cls.minha)

    def setUp(self):
        self.client.force_login(self.usuario)

    def test_lista_so_da_propria_barbearia(self):
        resposta = self.client.get('/clientes/')
        self.assertContains(resposta, 'João Pereira')
        self.assertNotContains(resposta, 'Cliente de fora')

    def test_busca_por_nome_e_telefone(self):
        self.assertContains(self.client.get('/clientes/?q=joão'), 'João Pereira')
        self.assertContains(self.client.get('/clientes/?q=98765'), 'João Pereira')
        self.assertNotContains(self.client.get('/clientes/?q=maria'), 'João Pereira')

    def test_cadastro_fica_na_barbearia_do_usuario(self):
        self.client.post('/clientes/novo/', {'nome': 'Novo Cliente'})
        self.assertEqual(Cliente.objects.get(nome='Novo Cliente').barbearia, self.minha)

    def test_ficha_de_outra_barbearia_nao_abre(self):
        self.assertEqual(self.client.get(f'/clientes/{self.de_fora.pk}/').status_code, 404)


class HorariosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from .models import Barbeiro

        cls.barbearia = Barbearia.objects.create(nome='Minha')
        cls.ricardo = Barbeiro.objects.create(barbearia=cls.barbearia, nome='Ricardo')
        cls.paulo = Barbeiro.objects.create(barbearia=cls.barbearia, nome='Paulo')
        cls.dono = Usuario.objects.create_user('dono', password='senha-de-teste-123', barbearia=cls.barbearia)
        cls.usuario_ricardo = Usuario.objects.create_user(
            'ricardo', password='senha-de-teste-123', barbearia=cls.barbearia, papel=Usuario.Papel.BARBEIRO
        )
        cls.ricardo.usuario = cls.usuario_ricardo
        cls.ricardo.save()

    def semana(self, **extra):
        dados = {'acao': 'semana', 'd0_ativo': 'on', 'd0_inicio1': '09:00', 'd0_fim1': '12:00',
                 'd0_inicio2': '13:00', 'd0_fim2': '19:00'}
        dados.update(extra)
        return dados

    def test_dono_ve_todos_os_barbeiros(self):
        self.client.force_login(self.dono)
        resposta = self.client.get('/horarios/')
        self.assertContains(resposta, 'Ricardo')
        self.assertContains(resposta, 'Paulo')
        self.assertContains(resposta, '/agendar/minha/')

    def test_barbeiro_so_ve_os_proprios_horarios(self):
        self.client.force_login(self.usuario_ricardo)
        self.assertRedirects(self.client.get('/horarios/'), f'/horarios/{self.ricardo.pk}/')
        self.assertEqual(self.client.get(f'/horarios/{self.paulo.pk}/').status_code, 404)

    def test_salvar_semana_com_almoco(self):
        self.client.force_login(self.dono)
        self.client.post(f'/horarios/{self.ricardo.pk}/', self.semana())
        self.assertEqual([str(h) for h in self.ricardo.horarios.all()], ['Segunda 09:00-12:00', 'Segunda 13:00-19:00'])

    def test_salvar_de_novo_substitui_os_turnos(self):
        self.client.force_login(self.dono)
        self.client.post(f'/horarios/{self.ricardo.pk}/', self.semana())
        self.client.post(f'/horarios/{self.ricardo.pk}/', {'acao': 'semana', 'd5_ativo': 'on', 'd5_inicio1': '08:00', 'd5_fim1': '12:00'})
        self.assertEqual([str(h) for h in self.ricardo.horarios.all()], ['Sábado 08:00-12:00'])

    def test_tarde_antes_da_manha_e_recusada(self):
        self.client.force_login(self.dono)
        resposta = self.client.post(f'/horarios/{self.ricardo.pk}/', self.semana(d0_inicio2='11:00'))
        self.assertContains(resposta, 'a tarde precisa começar depois do fim da manhã')
        self.assertFalse(self.ricardo.horarios.exists())

    def test_folga(self):
        self.client.force_login(self.dono)
        self.client.post(f'/horarios/{self.ricardo.pk}/', {'acao': 'folga', 'data_inicio': '2099-01-10', 'data_fim': '2099-01-12', 'motivo': 'Férias'})
        folga = self.ricardo.bloqueios.get()
        self.assertEqual(str(folga), '10/01 a 12/01/2099')
        self.client.post(f'/horarios/{self.ricardo.pk}/folgas/{folga.pk}/remover/')
        self.assertFalse(self.ricardo.bloqueios.exists())
