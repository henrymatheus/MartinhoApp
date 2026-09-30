from datetime import timedelta

from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateTimeRangeField, RangeBoundary, RangeOperators
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models
from django.db.models import Q, Sum
from django.utils import timezone

from apps.cadastros.models import Barbeiro, Cliente, Servico
from apps.contas.models import PertenceABarbearia


class TsTzRange(models.Func):
    """A função tstzrange(inicio, fim) do PostgreSQL: um intervalo de tempo."""

    function = 'TSTZRANGE'
    output_field = DateTimeRangeField()


def mesma_barbearia(obj, *relacionados):
    """Garante que cliente, barbeiro e serviço são da mesma barbearia do registro."""
    erros = {}
    for campo in relacionados:
        relacionado = getattr(obj, campo, None)
        if relacionado is not None and relacionado.barbearia_id != obj.barbearia_id:
            erros[campo] = 'Pertence a outra barbearia.'
    if erros:
        raise ValidationError(erros)


class Agendamento(PertenceABarbearia):
    class Status(models.TextChoices):
        AGENDADO = 'agendado', 'Agendado'
        CONCLUIDO = 'concluido', 'Concluído'
        CANCELADO = 'cancelado', 'Cancelado'
        FALTOU = 'faltou', 'Faltou'

    # PROTECT: não dá para apagar um cliente, barbeiro ou serviço que tem
    # agendamentos. O caminho certo é desativá-lo.
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='agendamentos')
    barbeiro = models.ForeignKey(Barbeiro, on_delete=models.PROTECT, related_name='agendamentos')
    servico = models.ForeignKey(
        Servico, on_delete=models.PROTECT, related_name='agendamentos', verbose_name='serviço'
    )
    inicio = models.DateTimeField('início')
    # Calculado a partir da duração do serviço se não for informado.
    fim = models.DateTimeField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.AGENDADO)
    observacoes = models.TextField('observações', blank=True)

    class Meta:
        ordering = ['inicio']
        indexes = [models.Index(fields=['barbearia', 'inicio'])]
        constraints = [
            models.CheckConstraint(condition=Q(fim__gt=models.F('inicio')), name='agendamento_fim_depois_do_inicio'),
            # A regra "o mesmo barbeiro não pode ter dois agendamentos no mesmo
            # horário", garantida pelo próprio PostgreSQL.
            #
            # Ela recusa gravar dois agendamentos em que:
            #   - o barbeiro é o mesmo (RangeOperators.EQUAL), e
            #   - os intervalos [inicio, fim) se sobrepõem (RangeOperators.OVERLAPS).
            # O intervalo é fechado no início e aberto no fim: um horário das
            # 14:00 às 14:30 não conflita com outro que começa às 14:30.
            # Agendamentos cancelados não ocupam o horário (condition).
            #
            # Por que no banco e não só em Python: se duas pessoas agendarem
            # ao mesmo tempo, as duas checagens em Python podem passar antes de
            # qualquer uma gravar. O banco é o único ponto que vê as duas.
            # O Django também usa essa constraint no full_clean(), então o
            # admin e os formulários mostram a mensagem abaixo em vez de um erro.
            ExclusionConstraint(
                name='agendamento_sem_conflito_de_horario',
                expressions=[
                    (TsTzRange('inicio', 'fim', RangeBoundary()), RangeOperators.OVERLAPS),
                    ('barbeiro', RangeOperators.EQUAL),
                ],
                condition=~Q(status='cancelado'),
                violation_error_message='Esse barbeiro já tem um agendamento nesse horário.',
            ),
        ]

    def __str__(self):
        inicio = timezone.localtime(self.inicio).strftime('%d/%m/%Y %H:%M')
        return f'{inicio} · {self.cliente} com {self.barbeiro}'

    def calcular_fim(self):
        if self.fim is None and self.inicio is not None and self.servico_id is not None:
            self.fim = self.inicio + timedelta(minutes=self.servico.duracao_minutos)

    def clean(self):
        # Roda antes da checagem das constraints no full_clean(), por isso o
        # fim já está calculado quando o Django verifica o conflito.
        self.calcular_fim()
        mesma_barbearia(self, 'cliente', 'barbeiro', 'servico')

    def save(self, *args, **kwargs):
        self.calcular_fim()
        super().save(*args, **kwargs)


class Atendimento(PertenceABarbearia):
    """
    Um atendimento realizado: é o histórico do cliente.

    Nasce ao concluir um agendamento ou é registrado direto, para quem chega
    sem hora marcada.
    """

    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='atendimentos')
    # SET_NULL: se o barbeiro for apagado, o histórico continua existindo.
    barbeiro = models.ForeignKey(
        Barbeiro, on_delete=models.SET_NULL, null=True, blank=True, related_name='atendimentos'
    )
    agendamento = models.OneToOneField(
        Agendamento, on_delete=models.SET_NULL, null=True, blank=True, related_name='atendimento'
    )
    data = models.DateField(default=timezone.localdate)
    observacoes = models.TextField('observações', blank=True)

    class Meta:
        ordering = ['-data', '-criado_em']
        indexes = [models.Index(fields=['barbearia', 'cliente', 'data'])]

    def __str__(self):
        return f'{self.data:%d/%m/%Y} · {self.cliente}'

    def clean(self):
        mesma_barbearia(self, 'cliente', 'barbeiro', 'agendamento')

    @property
    def total(self):
        return self.itens.aggregate(total=Sum('valor'))['total'] or 0


class ItemAtendimento(models.Model):
    """
    Um serviço prestado em um atendimento.

    A descrição e o valor são copiados do serviço no momento do atendimento.
    Assim, se o preço do corte subir, o histórico continua mostrando o valor
    que o cliente realmente pagou.
    """

    atendimento = models.ForeignKey(Atendimento, on_delete=models.CASCADE, related_name='itens')
    servico = models.ForeignKey(
        Servico, on_delete=models.SET_NULL, null=True, blank=True, related_name='+', verbose_name='serviço'
    )
    descricao = models.CharField('descrição', max_length=120, blank=True)
    valor = models.DecimalField(max_digits=8, decimal_places=2, blank=True)

    class Meta:
        verbose_name = 'item do atendimento'
        verbose_name_plural = 'itens do atendimento'

    def __str__(self):
        return self.descricao

    def preencher_do_servico(self):
        if self.servico_id is not None:
            if not self.descricao:
                self.descricao = self.servico.nome
            if self.valor is None:
                self.valor = self.servico.preco

    def clean(self):
        self.preencher_do_servico()
        try:
            barbearia_id = self.atendimento.barbearia_id
        except ObjectDoesNotExist:
            # No admin, o item é validado antes de o atendimento ser gravado.
            barbearia_id = None
        if self.servico_id is not None and barbearia_id and self.servico.barbearia_id != barbearia_id:
            raise ValidationError({'servico': 'Pertence a outra barbearia.'})
        if not self.descricao or self.valor is None:
            raise ValidationError('Escolha um serviço ou preencha descrição e valor.')

    def save(self, *args, **kwargs):
        self.preencher_do_servico()
        super().save(*args, **kwargs)
