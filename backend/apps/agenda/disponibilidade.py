"""
Cálculo dos horários livres dos barbeiros, usado na página de agendamento
do cliente e nos avisos da agenda.

Um horário está livre quando:
1. cabe inteiro dentro de um turno de trabalho do barbeiro naquele dia
   (um corte de 30 min às 11:45 não cabe num turno que termina às 12:00);
2. o barbeiro não está ausente nesse trecho (folga, férias ou falta,
   de dia inteiro ou de parte do dia);
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


def sobrepoe(inicio_a, fim_a, inicio_b, fim_b):
    """Dois trechos se sobrepõem se um começa antes de o outro terminar, e vice-versa."""
    return inicio_a < fim_b and fim_a > inicio_b


def ausencias_no_dia(barbeiro, dia):
    """Trechos (início, fim) em que o barbeiro está ausente naquele dia."""
    bloqueios = Bloqueio.objects.filter(barbeiro=barbeiro, data_inicio__lte=dia, data_fim__gte=dia)
    return [b.intervalo_em(dia) for b in bloqueios]


def ausente_o_dia_todo(barbeiro, dia):
    return Bloqueio.objects.filter(
        barbeiro=barbeiro, data_inicio__lte=dia, data_fim__gte=dia, hora_inicio__isnull=True
    ).exists()


def ausente_em(barbeiro, inicio, fim):
    """O barbeiro está ausente em algum momento entre inicio e fim?"""
    dia = timezone.localdate(inicio)
    return any(sobrepoe(inicio, fim, a_inicio, a_fim) for a_inicio, a_fim in ausencias_no_dia(barbeiro, dia))


def dias_de_atendimento(barbeiro, a_partir_de=None):
    """
    Os próximos DIAS_A_FRENTE dias em que o barbeiro tem turno e não está
    ausente o dia inteiro. (Uma ausência de parte do dia não tira o dia.)
    """
    hoje = a_partir_de or timezone.localdate()
    dias_com_turno = set(barbeiro.horarios.values_list('dia_semana', flat=True))
    fim = hoje + timedelta(days=DIAS_A_FRENTE)
    folgas = list(
        barbeiro.bloqueios.filter(data_fim__gte=hoje, data_inicio__lte=fim, hora_inicio__isnull=True)
    )
    dias = []
    for n in range(DIAS_A_FRENTE):
        dia = hoje + timedelta(days=n)
        if dia.weekday() in dias_com_turno and not any(f.data_inicio <= dia <= f.data_fim for f in folgas):
            dias.append(dia)
    return dias


def horarios_livres(barbeiro, servico, dia, agora=None):
    """Lista de inícios possíveis (datetime com fuso) para o serviço naquele dia."""
    agora = agora or timezone.now()
    duracao = timedelta(minutes=servico.duracao_minutos)

    ausencias = ausencias_no_dia(barbeiro, dia)
    ocupados = ausencias + [
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
            livre = not any(sobrepoe(inicio, fim, o_inicio, o_fim) for o_inicio, o_fim in ocupados)
            if inicio >= primeiro_permitido and livre:
                livres.append(inicio)
            inicio += INTERVALO
    return livres


def esta_livre(barbeiro, servico, inicio, agora=None):
    """Confere se um horário escolhido ainda está entre os livres."""
    dia = timezone.localdate(inicio)
    return inicio in horarios_livres(barbeiro, servico, dia, agora)


def dias_com_algum_barbeiro(barbeiros, a_partir_de=None):
    """Dias em que pelo menos um dos barbeiros atende, em ordem."""
    dias = set()
    for barbeiro in barbeiros:
        dias.update(dias_de_atendimento(barbeiro, a_partir_de))
    return sorted(dias)


def barbeiros_do_dia(barbeiros, servico, dia, agora=None):
    """
    Os barbeiros que têm horário livre naquele dia, cada um com a sua lista
    de horários. Quem está ausente ou com a agenda cheia não entra.
    """
    resultado = []
    for barbeiro in barbeiros:
        livres = horarios_livres(barbeiro, servico, dia, agora)
        if livres:
            resultado.append((barbeiro, livres))
    return resultado
