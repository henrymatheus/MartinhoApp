from django.contrib.auth.models import AbstractUser
from django.db import models


class Barbearia(models.Model):
    """Cada barbearia cliente do Martinho. Todo dado do sistema pertence a uma."""

    nome = models.CharField(max_length=120)
    telefone = models.CharField(max_length=20, blank=True)
    endereco = models.CharField('endereço', max_length=255, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nome']

    def __str__(self):
        return self.nome


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
