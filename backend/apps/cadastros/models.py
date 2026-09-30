from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.contas.models import PertenceABarbearia


class Barbeiro(PertenceABarbearia):
    nome = models.CharField(max_length=120)
    telefone = models.CharField(max_length=20, blank=True)
    # Barbeiro desativado some da agenda, mas continua no histórico.
    ativo = models.BooleanField(default=True)
    # Opcional: um barbeiro pode existir sem ter login no sistema.
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='barbeiro',
    )

    class Meta:
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Servico(PertenceABarbearia):
    nome = models.CharField(max_length=120)
    # DecimalField em vez de float: float guarda 0.1 como 0.1000000000000000055…
    # e isso gera centavos errados em somas de dinheiro.
    preco = models.DecimalField('preço', max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])
    # A duração define o fim do agendamento, que é usado para detectar conflitos.
    duracao_minutos = models.PositiveSmallIntegerField(
        'duração (minutos)', default=30, validators=[MinValueValidator(5)]
    )
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'serviço'
        constraints = [
            models.UniqueConstraint(fields=['barbearia', 'nome'], name='servico_nome_unico_por_barbearia'),
        ]

    def __str__(self):
        return self.nome


class Cliente(PertenceABarbearia):
    nome = models.CharField(max_length=120)
    telefone = models.CharField(max_length=20, blank=True)
    email = models.EmailField('e-mail', blank=True)
    data_nascimento = models.DateField('data de nascimento', null=True, blank=True)
    endereco = models.CharField('endereço', max_length=255, blank=True)
    observacoes = models.TextField('observações', blank=True)

    class Meta:
        ordering = ['nome']
        indexes = [models.Index(fields=['barbearia', 'nome'])]

    def __str__(self):
        return self.nome
