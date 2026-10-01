from datetime import datetime, time, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.contas.models import PertenceABarbearia
from apps.contas.telefones import link_whatsapp, mesmo_telefone, somente_digitos


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


def encontrar_ou_criar_cliente(barbearia, nome, telefone):
    """
    Quem já é cliente é reconhecido pelo telefone, e o agendamento vai para a
    ficha existente, com o histórico. Um telefone novo cria um cliente novo.
    Usado pela página do cliente e pelo registro de atendimento sem horário.
    """
    candidatos = Cliente.objects.filter(barbearia=barbearia, telefone__contains=somente_digitos(telefone)[-4:])
    for cliente in candidatos:
        if mesmo_telefone(cliente.telefone, telefone):
            return cliente
    return Cliente.objects.create(barbearia=barbearia, nome=nome, telefone=telefone)


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
    """
    Período em que o barbeiro não atende: folga, férias, falta, consulta etc.

    Sem horário, vale para os dias inteiros de data_inicio a data_fim.
    Com horário (só para um único dia), vale apenas aquele trecho: por
    exemplo "hoje, das 13:00 às 18:00" ou "saiu às 15:00".
    """

    barbeiro = models.ForeignKey(Barbeiro, on_delete=models.CASCADE, related_name='bloqueios')
    data_inicio = models.DateField('de')
    data_fim = models.DateField('até')
    hora_inicio = models.TimeField('das', null=True, blank=True)
    hora_fim = models.TimeField('às', null=True, blank=True)
    motivo = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ['data_inicio', 'hora_inicio']
        verbose_name = 'ausência'
        verbose_name_plural = 'ausências (folgas, férias, faltas)'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(data_fim__gte=models.F('data_inicio')), name='bloqueio_fim_depois_do_inicio'
            ),
            # Horário: os dois preenchidos (e fim depois do início) ou nenhum.
            models.CheckConstraint(
                condition=(
                    models.Q(hora_inicio__isnull=True, hora_fim__isnull=True)
                    | models.Q(hora_inicio__isnull=False, hora_fim__isnull=False, hora_fim__gt=models.F('hora_inicio'))
                ),
                name='bloqueio_horario_completo',
            ),
        ]

    def __str__(self):
        if self.dia_parcial:
            return f'{self.data_inicio:%d/%m/%Y}, das {self.hora_inicio:%H:%M} às {self.hora_fim:%H:%M}'
        if self.data_inicio == self.data_fim:
            return f'{self.data_inicio:%d/%m/%Y}'
        return f'{self.data_inicio:%d/%m} a {self.data_fim:%d/%m/%Y}'

    @property
    def dia_parcial(self):
        return self.hora_inicio is not None

    def intervalo_em(self, dia):
        """
        O trecho (início, fim) em que o barbeiro está ausente naquele dia,
        com fuso. Dia inteiro = da meia-noite à meia-noite seguinte.
        """
        if self.dia_parcial:
            return (
                timezone.make_aware(datetime.combine(dia, self.hora_inicio)),
                timezone.make_aware(datetime.combine(dia, self.hora_fim)),
            )
        inicio = timezone.make_aware(datetime.combine(dia, time.min))
        return inicio, timezone.make_aware(datetime.combine(dia + timedelta(days=1), time.min))

    def clean(self):
        if self.data_inicio and self.data_fim and self.data_fim < self.data_inicio:
            raise ValidationError({'data_fim': 'A data final precisa ser igual ou depois da inicial.'})
        if (self.hora_inicio is None) != (self.hora_fim is None):
            raise ValidationError('Para uma ausência de parte do dia, preencha o horário de início e o de fim.')
        if self.dia_parcial:
            if self.data_inicio != self.data_fim:
                raise ValidationError('Ausência com horário vale para um único dia.')
            if self.hora_fim <= self.hora_inicio:
                raise ValidationError({'hora_fim': 'O fim precisa ser depois do início.'})
