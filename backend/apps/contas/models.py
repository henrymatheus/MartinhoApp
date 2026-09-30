from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.text import slugify

from .telefones import link_whatsapp


class Barbearia(models.Model):
    """Cada barbearia cliente do Martinho. Todo dado do sistema pertence a uma."""

    nome = models.CharField(max_length=120)
    # Parte do endereço da página de agendamento: /agendar/<slug>/.
    # Gerado a partir do nome na primeira gravação ("Barbearia do João" ->
    # "barbearia-do-joao") e pode ser trocado no admin.
    slug = models.SlugField('endereço da página', max_length=60, unique=True, blank=True)
    telefone = models.CharField(max_length=20, blank=True, help_text='Aparece na página de agendamento para contato.')
    endereco = models.CharField('endereço', max_length=255, blank=True)
    agendamento_online = models.BooleanField(
        'agendamento online', default=True, help_text='Permite que clientes agendem pela página pública.'
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nome']

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.gerar_slug()
        super().save(*args, **kwargs)

    def gerar_slug(self):
        base = slugify(self.nome)[:50] or 'barbearia'
        slug, n = base, 2
        while Barbearia.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug, n = f'{base}-{n}', n + 1
        return slug

    def link_whatsapp(self, mensagem=''):
        return link_whatsapp(self.telefone, mensagem)


class Usuario(AbstractUser):
    """
    Quem faz login no sistema.

    Estende o usuário padrão do Django. O Django recomenda um model de
    usuário próprio desde o início, porque trocar depois da primeira
    migration é muito trabalhoso.
    """

    class Papel(models.TextChoices):
        DONO = 'dono', 'Dono'
        BARBEIRO = 'barbeiro', 'Barbeiro'

    # Pode ficar vazio só para o superusuário (você, administrando o sistema).
    barbearia = models.ForeignKey(
        Barbearia,
        on_delete=models.PROTECT,
        related_name='usuarios',
        null=True,
        blank=True,
    )
    papel = models.CharField(max_length=10, choices=Papel.choices, default=Papel.DONO)


class PertenceABarbearia(models.Model):
    """
    Base para os models que pertencem a uma barbearia.

    O campo `barbearia` em cada tabela é o que isola os dados de uma
    barbearia das outras: toda consulta da API vai filtrar por ele.
    """

    # PROTECT: o banco recusa apagar uma barbearia que ainda tem dados.
    barbearia = models.ForeignKey(Barbearia, on_delete=models.PROTECT)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class InscricaoPush(models.Model):
    """
    Um celular (ou navegador) que aceitou receber avisos do Martinho.

    Quando alguém toca em "Ativar avisos", o navegador gera um endereço
    exclusivo (endpoint) e duas chaves de criptografia. Guardamos isso para
    enviar a notificação depois. Uma pessoa pode ter vários aparelhos.
    """

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='inscricoes_push')
    endpoint = models.URLField(max_length=500, unique=True)
    p256dh = models.CharField(max_length=200)
    auth = models.CharField(max_length=100)
    navegador = models.CharField(max_length=200, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'aparelho com avisos'
        verbose_name_plural = 'aparelhos com avisos'

    def __str__(self):
        return f'{self.usuario} · {self.navegador[:40] or "aparelho"}'
