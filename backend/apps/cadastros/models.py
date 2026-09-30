from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from apps.contas.models import PertenceABarbearia
from apps.contas.telefones import link_whatsapp


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

    def aniversario_em(self, dia):
        return (
            self.data_nascimento is not None
            and (self.data_nascimento.day, self.data_nascimento.month) == (dia.day, dia.month)
        )

    def link_whatsapp(self, mensagem=''):
        return link_whatsapp(self.telefone, mensagem)


class HorarioTrabalho(models.Model):
    """
    Um turno de trabalho do barbeiro num dia da semana.

    Um dia pode ter dois turnos, por exemplo 09:00-12:00 e 13:00-19:00, e
    o intervalo entre eles é o almoço. Dia sem turno = barbeiro não atende.
    """

    class DiaSemana(models.IntegerChoices):
        # Mesma numeração do Python: date.weekday() devolve 0 para segunda.
        SEGUNDA = 0, 'Segunda'
        TERCA = 1, 'Terça'
        QUARTA = 2, 'Quarta'
        QUINTA = 3, 'Quinta'
        SEXTA = 4, 'Sexta'
        SABADO = 5, 'Sábado'
        DOMINGO = 6, 'Domingo'

    barbeiro = models.ForeignKey(Barbeiro, on_delete=models.CASCADE, related_name='horarios')
    dia_semana = models.PositiveSmallIntegerField('dia da semana', choices=DiaSemana.choices)
    inicio = models.TimeField('início')
    fim = models.TimeField()

    class Meta:
        ordering = ['dia_semana', 'inicio']
        verbose_name = 'horário de trabalho'
        verbose_name_plural = 'horários de trabalho'
        constraints = [
            models.CheckConstraint(condition=models.Q(fim__gt=models.F('inicio')), name='horario_fim_depois_do_inicio'),
        ]

    def __str__(self):
        return f'{self.get_dia_semana_display()} {self.inicio:%H:%M}-{self.fim:%H:%M}'


class Bloqueio(models.Model):
    """Dias em que o barbeiro não atende: folga, férias, curso etc."""

    barbeiro = models.ForeignKey(Barbeiro, on_delete=models.CASCADE, related_name='bloqueios')
    data_inicio = models.DateField('de')
    data_fim = models.DateField('até')
    motivo = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ['data_inicio']
        verbose_name = 'folga ou férias'
        verbose_name_plural = 'folgas e férias'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(data_fim__gte=models.F('data_inicio')), name='bloqueio_fim_depois_do_inicio'
            ),
        ]

    def __str__(self):
        if self.data_inicio == self.data_fim:
            return f'{self.data_inicio:%d/%m/%Y}'
        return f'{self.data_inicio:%d/%m} a {self.data_fim:%d/%m/%Y}'

    def clean(self):
        if self.data_inicio and self.data_fim and self.data_fim < self.data_inicio:
            raise ValidationError({'data_fim': 'A data final precisa ser igual ou depois da inicial.'})
