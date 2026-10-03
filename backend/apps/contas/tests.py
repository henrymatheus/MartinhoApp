from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from apps.cadastros.models import Cliente

from .models import Barbearia, Usuario


class AdminIsoladoPorBarbeariaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.minha = Barbearia.objects.create(nome='Minha')
        cls.outra = Barbearia.objects.create(nome='Outra')
        Cliente.objects.create(barbearia=cls.minha, nome='Cliente da minha')
        Cliente.objects.create(barbearia=cls.outra, nome='Cliente da outra')
        cls.dono = Usuario.objects.create_user('dono', password='senha-de-teste-123', is_staff=True, barbearia=cls.minha)
        cls.dono.user_permissions.add(*Permission.objects.filter(codename__endswith='_cliente'))

    def setUp(self):
        self.client.force_login(self.dono)

    def test_lista_mostra_so_clientes_da_propria_barbearia(self):
        resposta = self.client.get(reverse('admin:cadastros_cliente_changelist'))
        self.assertContains(resposta, 'Cliente da minha')
        self.assertNotContains(resposta, 'Cliente da outra')

    def test_novo_cliente_fica_na_barbearia_do_usuario(self):
        self.client.post(reverse('admin:cadastros_cliente_add'), {'nome': 'Novo'})
        self.assertEqual(Cliente.objects.get(nome='Novo').barbearia, self.minha)
