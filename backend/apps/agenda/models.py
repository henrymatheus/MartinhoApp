from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone

from apps.cadastros.models import Barbeiro, Cliente, Servico
from apps.contas.models import PertenceABarbearia

MENSAGEM_CONFLITO = 'Esse barbeiro já tem um agendamento nesse horário.'


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
        indexes = [
            models.Index(fields=['barbearia', 'inicio']),
            # Acelera a busca de conflitos, que filtra por barbeiro e horário.
            models.Index(fields=['barbeiro', 'inicio']),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(fim__gt=models.F('inicio')), name='agendamento_fim_depois_do_inicio'),
        ]

    def __str__(self):
        inicio = timezone.localtime(self.inicio).strftime('%d/%m/%Y %H:%M')
        return f'{inicio} · {self.cliente} com {self.barbeiro}'

    def calcular_fim(self):
        if self.fim is None and self.inicio is not None and self.servico_id is not None:
            self.fim = self.inicio + timedelta(minutes=self.servico.duracao_minutos)

    def conflitos(self):
        """
        Outros agendamentos do mesmo barbeiro que se sobrepõem a este.

        Dois horários se sobrepõem quando um começa antes de o outro terminar
        (inicio < fim do outro) e termina depois de o outro começar
        (fim > inicio do outro). Por isso 14:00-14:30 e 14:30-15:00 não
        conflitam. Agendamentos cancelados não ocupam o horário.
        """
        return (
            Agendamento.objects.filter(barbeiro_id=self.barbeiro_id, inicio__lt=self.fim, fim__gt=self.inicio)
            .exclude(status=self.Status.CANCELADO)
            .exclude(pk=self.pk)
        )

    def verificar_conflito(self):
        if self.status != self.Status.CANCELADO and self.conflitos().exists():
            raise ValidationError(MENSAGEM_CONFLITO)

    def clean(self):
        # Chamado pelo admin e pelos formulários: mostra a mensagem no campo
        # em vez de um erro na tela.
        self.calcular_fim()
        mesma_barbearia(self, 'cliente', 'barbeiro', 'servico')
        if self.barbeiro_id and self.fim:
            self.verificar_conflito()

    def save(self, *args, **kwargs):
        """
        Grava o agendamento verificando conflito de horário.

        A verificação fica também aqui, e não só no clean(), para valer em
        qualquer caminho: admin, API, shell ou scripts.

        Duas pessoas podem tentar agendar o mesmo barbeiro ao mesmo tempo. Se
        as duas verificassem ao mesmo tempo, ambas veriam o horário livre e
        ambas gravariam. Para evitar isso, dentro de uma transação, travamos a
        linha do barbeiro (select_for_update): a segunda gravação espera a
        primeira terminar e, quando verifica, já enxerga o horário ocupado.
        No PostgreSQL (produção) essa trava é real. O SQLite (desenvolvimento)
        ignora o select_for_update, o que não é problema com um só usuário.
        """
        self.calcular_fim()
        with transaction.atomic():
            Barbeiro.objects.select_for_update().filter(pk=self.barbeiro_id).first()
            self.verificar_conflito()
            super().save(*args, **kwargs)

    @transaction.atomic
    def concluir(self):
        """
        Marca como concluído e registra o atendimento no histórico do cliente,
        com o serviço e o preço atuais. Tudo ou nada: se algo falhar, nada é gravado.
        """
        self.status = self.Status.CONCLUIDO
        self.save()
        atendimento, criado = Atendimento.objects.get_or_create(
            agendamento=self,
            defaults={
                'barbearia': self.barbearia,
                'cliente': self.cliente,
                'barbeiro': self.barbeiro,
                'data': timezone.localdate(self.inicio),
                'observacoes': self.observacoes,
            },
        )
        if criado:
            ItemAtendimento.objects.create(atendimento=atendimento, servico=self.servico)
        return atendimento

    def mensagem_lembrete(self):
        inicio = timezone.localtime(self.inicio)
        return (
            f'Olá, {self.cliente.nome.split()[0]}! Lembrando do seu horário na '
            f'{self.barbearia.nome}: {inicio:%d/%m} às {inicio:%H:%M}, '
            f'{self.servico.nome.lower()} com {self.barbeiro.nome}.'
        )


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
        # itens.all() aproveita o prefetch_related da tela de histórico, então
        # a soma não faz uma consulta ao banco por atendimento.
        return sum((item.valor for item in self.itens.all()), Decimal('0'))


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
