"""
Cálculo dos horários livres de um barbeiro, usado na página de agendamento
do cliente.

Um horário está livre quando:
1. cabe inteiro dentro de um turno de trabalho do barbeiro naquele dia
   (um corte de 30 min às 11:45 não cabe num turno que termina às 12:00);
2. o dia não está numa folga ou nas férias do barbeiro;
3. não se sobrepõe a nenhum agendamento (cancelados não contam);
4. começa com uma antecedência mínima em relação a agora.

Os horários são oferecidos a cada INTERVALO minutos a partir do início do
turno: 09:00, 09:15, 09:30...
"""

from datetime import datetime, timedelta

from django.utils import timezone

from apps.cadastros.models import Bloqueio

from .models import Agendamento

INTERVALO = timedelta(minutes=15)
ANTECEDENCIA_MINIMA = timedelta(minutes=60)
DIAS_A_FRENTE = 30


def dias_de_atendimento(barbeiro, a_partir_de=None):
    """Os próximos DIAS_A_FRENTE dias em que o barbeiro tem turno e não está de folga."""
    hoje = a_partir_de or timezone.localdate()
    dias_com_turno = set(barbeiro.horarios.values_list('dia_semana', flat=True))
    fim = hoje + timedelta(days=DIAS_A_FRENTE)
    bloqueios = list(barbeiro.bloqueios.filter(data_fim__gte=hoje, data_inicio__lte=fim))
    dias = []
    for n in range(DIAS_A_FRENTE):
        dia = hoje + timedelta(days=n)
        if dia.weekday() in dias_com_turno and not any(b.data_inicio <= dia <= b.data_fim for b in bloqueios):
            dias.append(dia)
    return dias


def horarios_livres(barbeiro, servico, dia, agora=None):
    """Lista de inícios possíveis (datetime com fuso) para o serviço naquele dia."""
    agora = agora or timezone.now()
    duracao = timedelta(minutes=servico.duracao_minutos)

    if Bloqueio.objects.filter(barbeiro=barbeiro, data_inicio__lte=dia, data_fim__gte=dia).exists():
        return []

    ocupados = [
        (ag.inicio, ag.fim)
        for ag in Agendamento.objects.filter(barbeiro=barbeiro, inicio__date=dia).exclude(
            status=Agendamento.Status.CANCELADO
        )
    ]
    primeiro_permitido = agora + ANTECEDENCIA_MINIMA

    livres = []
    for turno in barbeiro.horarios.filter(dia_semana=dia.weekday()):
        inicio = timezone.make_aware(datetime.combine(dia, turno.inicio))
        fim_turno = timezone.make_aware(datetime.combine(dia, turno.fim))
        while inicio + duracao <= fim_turno:
            fim = inicio + duracao
            sobrepoe = any(inicio < ocupado_fim and fim > ocupado_inicio for ocupado_inicio, ocupado_fim in ocupados)
            if inicio >= primeiro_permitido and not sobrepoe:
                livres.append(inicio)
            inicio += INTERVALO
    return livres


def esta_livre(barbeiro, servico, inicio, agora=None):
    """Confere se um horário escolhido ainda está entre os livres."""
    dia = timezone.localdate(inicio)
    return inicio in horarios_livres(barbeiro, servico, dia, agora)
