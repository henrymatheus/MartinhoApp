import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.contas.models import Barbearia, Usuario

from .models import Parceiro

PNG = b'\x89PNG\r\n\x1a\n' + b'\x00' * 64
JPG = b'\xff\xd8\xff\xe0' + b'\x00' * 64
SVG = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><rect width="10" height="10"/></svg>'

# As logos dos testes vão para uma pasta temporária, apagada no fim.
MEDIA_TESTES = tempfile.mkdtemp()


def logo(nome='logo.png', conteudo=PNG):
    return SimpleUploadedFile(nome, conteudo)


@override_settings(MEDIA_ROOT=MEDIA_TESTES)
class ParceirosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.minha = Barbearia.objects.create(nome='Minha', parceiros_habilitado=True)
        cls.outra = Barbearia.objects.create(nome='Outra', parceiros_habilitado=True)
        cls.dono = Usuario.objects.create_user('dono', password='senha-de-teste-123', barbearia=cls.minha)
        cls.barbeiro = Usuario.objects.create_user(
            'barbeiro', password='senha-de-teste-123', barbearia=cls.minha, papel=Usuario.Papel.BARBEIRO
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TESTES, ignore_errors=True)

    def setUp(self):
        self.client.force_login(self.dono)

    def cadastrar(self, nome='Loja X', arquivo=None, **extra):
        dados = {'nome': nome, 'logo': arquivo or logo(), 'link': '', 'ordem': '0'}
        dados.update(extra)
        return self.client.post('/parceiros/novo/', dados)

    def parceiro_de_fora(self):
        return Parceiro.objects.create(barbearia=self.outra, nome='Parceiro de fora', logo=logo())

    # Cadastro e validação do upload

    def test_cadastra_png_jpg_e_svg(self):
        self.cadastrar('A', logo('a.png', PNG))
        self.cadastrar('B', logo('b.JPEG', JPG))
        self.cadastrar('C', logo('c.svg', SVG))
        nomes = [p.logo.name for p in Parceiro.objects.filter(barbearia=self.minha).order_by('nome')]
        self.assertEqual([n.rsplit('.', 1)[1] for n in nomes], ['png', 'jpg', 'svg'])
        self.assertTrue(all(n.startswith(f'parceiros/{self.minha.pk}/') for n in nomes))

    def test_recusa_arquivo_maior_que_2_mb(self):
        resposta = self.cadastrar(arquivo=logo('grande.png', PNG + b'\x00' * (2 * 1024 * 1024)))
        self.assertContains(resposta, 'no máximo 2 MB')
        self.assertFalse(Parceiro.objects.exists())

    def test_recusa_formato_errado(self):
        self.assertContains(self.cadastrar(arquivo=logo('logo.gif', b'GIF89a')), 'PNG, JPG ou SVG')

    def test_recusa_arquivo_renomeado(self):
        resposta = self.cadastrar(arquivo=logo('virus.png', b'MZ\x90\x00 executavel'))
        self.assertContains(resposta, 'não é uma imagem PNG, JPG ou SVG válida')

    def test_recusa_svg_com_javascript(self):
        perigosos = [
            b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
            b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>',
            b'<svg xmlns="http://www.w3.org/2000/svg"><a href="javascript:alert(1)"><rect/></a></svg>',
            b'<svg xmlns="http://www.w3.org/2000/svg"><foreignObject><p>oi</p></foreignObject></svg>',
            b'<!DOCTYPE svg [<!ENTITY a "aaaa">]><svg xmlns="http://www.w3.org/2000/svg">&a;</svg>',
            b'<html><body>nao e svg</body></html>',
        ]
        for conteudo in perigosos:
            with self.subTest(conteudo=conteudo):
                self.assertEqual(self.cadastrar(arquivo=logo('x.svg', conteudo)).status_code, 200)
        self.assertFalse(Parceiro.objects.exists())

    def test_link_precisa_ser_http(self):
        self.assertEqual(self.cadastrar(link='javascript:alert(1)').status_code, 200)
        self.assertFalse(Parceiro.objects.exists())

    # Limite por barbearia

    def test_limite_padrao_de_3(self):
        for nome in 'ABCD':
            self.cadastrar(nome)
        self.assertEqual(Parceiro.objects.filter(barbearia=self.minha).count(), 3)
        self.assertNotContains(self.client.get('/parceiros/'), 'href="/parceiros/novo/"')

    def test_admin_libera_mais_parceiros(self):
        Barbearia.objects.filter(pk=self.minha.pk).update(limite_parceiros=5)
        for nome in 'ABCDE':
            self.cadastrar(nome)
        self.assertEqual(Parceiro.objects.filter(barbearia=self.minha).count(), 5)

    def test_limite_reduzido_esconde_os_excedentes_sem_apagar(self):
        for nome in 'ABC':
            self.cadastrar(nome)
        Barbearia.objects.filter(pk=self.minha.pk).update(limite_parceiros=2)
        self.minha.refresh_from_db()
        self.assertEqual([p.nome for p in self.minha.parceiros_visiveis()], ['A', 'B'])
        self.assertEqual(Parceiro.objects.filter(barbearia=self.minha).count(), 3)

    # Isolamento entre barbearias

    def test_lista_e_rodapes_mostram_so_os_da_propria_barbearia(self):
        self.cadastrar('Parceiro meu')
        self.parceiro_de_fora()
        for endereco in ['/parceiros/', '/clientes/', '/agendar/minha/']:
            with self.subTest(endereco=endereco):
                resposta = self.client.get(endereco)
                self.assertContains(resposta, 'alt="Parceiro meu"')
                self.assertNotContains(resposta, 'Parceiro de fora')

    def test_pagina_de_outra_barbearia_nao_mostra_os_meus(self):
        self.cadastrar('Parceiro meu')
        self.client.logout()
        self.assertNotContains(self.client.get('/agendar/outra/'), 'alt="Parceiro meu"')

    def test_nao_edita_nem_remove_parceiro_de_outra_barbearia(self):
        de_fora = self.parceiro_de_fora()
        self.assertEqual(self.client.get(f'/parceiros/{de_fora.pk}/editar/').status_code, 404)
        self.assertEqual(self.client.post(f'/parceiros/{de_fora.pk}/remover/').status_code, 404)
        self.assertTrue(Parceiro.objects.filter(pk=de_fora.pk).exists())

    # Edição e remoção

    def test_editar_sem_nova_logo_mantem_a_atual(self):
        self.cadastrar('Loja X')
        parceiro = Parceiro.objects.get()
        self.client.post(f'/parceiros/{parceiro.pk}/editar/', {'nome': 'Loja Y', 'link': 'loja.com.br', 'ordem': '1'})
        atualizado = Parceiro.objects.get()
        self.assertEqual(
            (atualizado.nome, atualizado.link, atualizado.logo.name), ('Loja Y', 'https://loja.com.br', parceiro.logo.name)
        )

    def test_trocar_e_remover_apagam_o_arquivo(self):
        self.cadastrar('Loja X')
        parceiro = Parceiro.objects.get()
        antigo = parceiro.logo.name
        self.client.post(f'/parceiros/{parceiro.pk}/editar/', {'nome': 'Loja X', 'logo': logo('nova.svg', SVG), 'ordem': '0'})
        novo = Parceiro.objects.get().logo
        self.assertNotEqual(novo.name, antigo)
        self.assertFalse(novo.storage.exists(antigo))
        self.client.post(f'/parceiros/{parceiro.pk}/remover/')
        self.assertFalse(Parceiro.objects.exists())
        self.assertFalse(novo.storage.exists(novo.name))

    # Permissões e liberação do recurso

    def test_barbeiro_e_barrado(self):
        self.client.force_login(self.barbeiro)
        self.assertEqual(self.client.get('/parceiros/').status_code, 403)
        self.assertEqual(self.cadastrar().status_code, 403)
        self.assertFalse(Parceiro.objects.exists())

    def test_recurso_desligado_some_e_bloqueia(self):
        self.cadastrar('Parceiro meu')
        Barbearia.objects.filter(pk=self.minha.pk).update(parceiros_habilitado=False)
        self.assertEqual(self.client.get('/parceiros/').status_code, 404)
        self.assertEqual(self.cadastrar('Outro').status_code, 404)
        self.assertNotContains(self.client.get('/clientes/'), 'alt="Parceiro meu"')
        self.assertNotContains(self.client.get('/agendar/minha/'), 'alt="Parceiro meu"')

    def test_recurso_comeca_desligado(self):
        self.assertFalse(Barbearia.objects.create(nome='Nova').parceiros_habilitado)
