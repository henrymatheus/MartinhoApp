"""
Balanço de atendimentos: o período escolhido e as contas.

Todas as contagens são feitas pelo banco (aggregate/annotate), numa consulta
para cada número. Assim o balanço de um mês inteiro custa as mesmas poucas
consultas que o de um dia.
"""

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from itertools import groupby

from django.db.models import Count, F, Q
from django.db.models.functions import TruncMonth

from apps.cadastros.models import Barbeiro
from apps.contas.models import Usuario

from .models import Agendamento, Atendimento

# Uma faixa personalizada maior que isto é cortada: evita uma tela com
# milhares de linhas. Para períodos longos, o CSV tem tudo.
MAXIMO_DIAS = 366

# Quantos atendimentos a lista da tela mostra. Os números do topo sempre
# consideram o período inteiro.
MAXIMO_NA_LISTA = 500


def primeiro_do_mes(dia):
    return dia.replace(day=1)


def ultimo_do_mes(dia):
    return dia.replace(day=calendar.monthrange(dia.year, dia.month)[1])


def mes_anterior(dia):
    return primeiro_do_mes(primeiro_do_mes(dia) - timedelta(days=1))


def ler_data(texto):
    try:
        return date.fromisoformat(texto)
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class Periodo:
    """
    Um intervalo de datas, de `inicio` a `fim` (os dois dias incluídos).

    tipo: 'dia', 'semana' (segunda a domingo), 'mes' ou 'livre' (de/até
    escolhidos pelo usuário). O tipo define para onde as setas ‹ › andam.
    """

    tipo: str
    inicio: date
    fim: date

    PADRAO = 'semana'

    @classmethod
    def do_tipo(cls, tipo, referencia):
        """O dia, a semana ou o mês que contém a data de referência."""
        if tipo == 'dia':
            return cls('dia', referencia, referencia)
        if tipo == 'mes':
            return cls('mes', primeiro_do_mes(referencia), ultimo_do_mes(referencia))
        segunda = referencia - timedelta(days=referencia.weekday())
        return cls('semana', segunda, segunda + timedelta(days=6))

    @classmethod
    def da_requisicao(cls, parametros, hoje):
        """
        Lê o período da URL. Qualquer valor inválido cai no padrão (esta
        semana), em vez de dar erro: o usuário sempre vê alguma coisa.
        """
        tipo = parametros.get('periodo', cls.PADRAO)
        if tipo == 'livre':
            de, ate = ler_data(parametros.get('de')), ler_data(parametros.get('ate'))
            if de and ate:
                if de > ate:
                    de, ate = ate, de
                ate = min(ate, de + timedelta(days=MAXIMO_DIAS - 1))
                return cls('livre', de, ate)
            tipo = cls.PADRAO
        if tipo not in ('dia', 'semana', 'mes'):
            tipo = cls.PADRAO
        return cls.do_tipo(tipo, ler_data(parametros.get('data')) or hoje)

    @property
    def dias(self):
        return (self.fim - self.inicio).days + 1

    def deslocar(self, sentido):
        """O período vizinho: sentido -1 é o anterior, +1 o seguinte."""
        if self.tipo == 'mes':
            referencia = mes_anterior(self.inicio) if sentido < 0 else self.fim + timedelta(days=1)
            return Periodo.do_tipo('mes', referencia)
        passo = timedelta(days=self.dias * sentido)
        return Periodo(self.tipo, self.inicio + passo, self.fim + passo)

    def para_comparar(self, hoje):
        """
        O período anterior, para a comparação "+12% que a semana passada".

        Se o período atual ainda está em andamento (contém hoje), o anterior
        é cortado no mesmo ponto: quarta-feira desta semana é comparada com
        segunda a quarta da semana passada, e não com a semana passada
        inteira, que deixaria qualquer semana em andamento "no vermelho".
        Período que ainda não começou não tem comparação.
        """
        if self.inicio > hoje:
            return None
        anterior = self.deslocar(-1)
        if self.inicio <= hoje <= self.fim:
            corte = anterior.inicio + (hoje - self.inicio)
            anterior = Periodo(anterior.tipo, anterior.inicio, min(anterior.fim, corte))
        return anterior

    def contem(self, dia):
        return self.inicio <= dia <= self.fim

    def parametros(self):
        """Parâmetros da URL que reproduzem este período."""
        if self.tipo == 'livre':
            return {'periodo': 'livre', 'de': self.inicio.isoformat(), 'ate': self.fim.isoformat()}
        return {'periodo': self.tipo, 'data': self.inicio.isoformat()}


def barbeiros_do_balanco(usuario):
    """
    De quais barbeiros o usuário pode ver o balanço.

    - Dono: todos da barbearia, inclusive os desativados (o histórico
      deles continua valendo).
    - Papel "barbeiro" ligado a um barbeiro: só ele mesmo.
    - Papel "barbeiro" sem ligação: nenhum. Diferente da tela Horários,
      aqui é o desempenho de cada um, então na dúvida não mostramos nada.
    """
    barbeiros = Barbeiro.objects.filter(barbearia=usuario.barbearia)
    if usuario.papel == Usuario.Papel.BARBEIRO:
        barbeiro = getattr(usuario, 'barbeiro', None)
        return barbeiros.filter(pk=barbeiro.pk) if barbeiro else barbeiros.none()
    return barbeiros


def atendimentos_do_periodo(barbearia, periodo, barbeiro=None):
    """Os atendimentos (concluídos ou avulsos) do período, de um barbeiro ou de todos."""
    atendimentos = Atendimento.objects.filter(barbearia=barbearia, data__range=(periodo.inicio, periodo.fim))
    if barbeiro is not None:
        atendimentos = atendimentos.filter(barbeiro=barbeiro)
    return atendimentos


def variacao(atual, anterior):
    """Diferença percentual, arredondada. None quando não há base de comparação."""
    if not anterior:
        return None
    return round((atual - anterior) / anterior * 100)


def dias_decorridos(periodo, hoje):
    """Dias do período que já aconteceram (a média por dia não conta dias futuros)."""
    if periodo.inicio > hoje:
        return 0
    return (min(periodo.fim, hoje) - periodo.inicio).days + 1


def calcular(barbearia, periodo, hoje, barbeiro=None):
    """
    Os números do painel. Por enquanto o balanço conta atendimentos e não
    mostra valores em dinheiro (decisão do dono). O preço continua sendo
    gravado no histórico, para quando os valores entrarem.
    """
    atendimentos = atendimentos_do_periodo(barbearia, periodo, barbeiro)
    # order_by() vazio: o Atendimento tem ordenação padrão (-data, -criado_em)
    # e, num values().annotate(), o Django colocaria esses campos no GROUP BY,
    # quebrando o agrupamento. Por isso cada agrupamento define a sua ordem.
    agrupado = atendimentos.order_by()

    resumo = agrupado.aggregate(quantidade=Count('id'), clientes=Count('cliente', distinct=True))
    quantidade = resumo['quantidade']
    por_dia = {linha['data']: linha['quantidade'] for linha in agrupado.values('data').annotate(quantidade=Count('id'))}
    por_barbeiro = (
        agrupado.values('barbeiro_id', 'barbeiro__nome')
        .annotate(quantidade=Count('id'))
        .order_by('-quantidade', 'barbeiro__nome')
    )

    agendamentos = Agendamento.objects.filter(
        barbearia=barbearia, inicio__date__range=(periodo.inicio, periodo.fim)
    )
    if barbeiro is not None:
        agendamentos = agendamentos.filter(barbeiro=barbeiro)
    perdas = agendamentos.aggregate(
        faltas=Count('id', filter=Q(status=Agendamento.Status.FALTOU)),
        cancelados=Count('id', filter=Q(status=Agendamento.Status.CANCELADO)),
    )

    comparacao = None
    anterior = periodo.para_comparar(hoje)
    if anterior is not None:
        quantidade_anterior = atendimentos_do_periodo(barbearia, anterior, barbeiro).count()
        comparacao = {
            'periodo': anterior,
            'quantidade': quantidade_anterior,
            'variacao': variacao(quantidade, quantidade_anterior),
            # Semana ou mês em andamento: comparado só até o mesmo dia.
            'parcial': periodo.tipo != 'dia' and periodo.contem(hoje),
        }

    decorridos = dias_decorridos(periodo, hoje)
    return {
        'quantidade': quantidade,
        'clientes': resumo['clientes'],
        # Uma casa decimal: 3,4 atendimentos por dia diz mais que "3".
        'media_por_dia': round(quantidade / decorridos, 1) if decorridos else 0,
        'faltas': perdas['faltas'],
        'cancelados': perdas['cancelados'],
        'grafico': grafico(periodo, atendimentos, por_dia, hoje),
        'por_barbeiro': list(por_barbeiro),
        'comparacao': comparacao,
        'dias': lista_por_dia(atendimentos, por_dia),
        'lista_cortada': quantidade > MAXIMO_NA_LISTA,
        'maximo_na_lista': MAXIMO_NA_LISTA,
    }


# Até este número de dias o gráfico tem uma barra por dia; acima disso
# (datas escolhidas, por exemplo um ano), uma barra por mês.
MAXIMO_BARRAS_DIARIAS = 35


def grafico(periodo, atendimentos, por_dia, hoje):
    """
    Barras do gráfico do painel: atendimentos por dia do período, incluindo
    os dias sem atendimento (barra vazia), ou por mês em faixas longas.

    A altura de cada barra é proporcional ao dia mais movimentado do
    período, que vira o topo do gráfico. Dias futuros ficam sem barra.
    Período de um dia só não tem gráfico: a lista do dia já diz tudo.
    """
    if periodo.dias == 1:
        return None
    barras = []
    if periodo.dias <= MAXIMO_BARRAS_DIARIAS:
        tipo = 'dia'
        for n in range(periodo.dias):
            dia = periodo.inicio + timedelta(days=n)
            barras.append({
                'data': dia,
                'periodo': Periodo.do_tipo('dia', dia),
                'quantidade': por_dia.get(dia, 0),
                'futuro': dia > hoje,
                'hoje': dia == hoje,
                # Num mês, rótulo só a cada 7 dias, para os números não se atropelarem no celular.
                'rotulo': periodo.dias <= 14 or n % 7 == 0,
            })
    else:
        tipo = 'mes'
        por_mes = {
            linha['mes']: linha['quantidade']
            for linha in atendimentos.order_by().annotate(mes=TruncMonth('data')).values('mes').annotate(quantidade=Count('id'))
        }
        mes = primeiro_do_mes(periodo.inicio)
        while mes <= periodo.fim:
            barras.append({
                'data': mes,
                'periodo': Periodo.do_tipo('mes', mes),
                'quantidade': por_mes.get(mes, 0),
                'futuro': mes > hoje,
                'hoje': mes == primeiro_do_mes(hoje),
                'rotulo': True,
            })
            mes = ultimo_do_mes(mes) + timedelta(days=1)

    maior = max((b['quantidade'] for b in barras), default=0)
    for barra in barras:
        barra['altura'] = round(barra['quantidade'] / maior * 100) if maior else 0
    return {'tipo': tipo, 'barras': barras, 'maior': maior}


def lista_detalhada(atendimentos):
    """
    Atendimentos com cliente, barbeiro e agendamento já carregados numa só
    consulta (select_related), sem uma consulta extra por linha.

    O horário vem do agendamento. Atendimento avulso (sem horário marcado)
    não tem hora: fica depois dos agendados do mesmo dia, na ordem em que
    foi registrado.
    """
    return atendimentos.select_related('cliente', 'barbeiro', 'agendamento').order_by(
        '-data', F('agendamento__inicio').asc(nulls_last=True), 'criado_em'
    )


def lista_por_dia(atendimentos, por_dia):
    """Dias do mais recente para o mais antigo, cada um com a quantidade e os atendimentos."""
    lista = lista_detalhada(atendimentos)[:MAXIMO_NA_LISTA]
    return [
        {'data': dia, 'quantidade': por_dia[dia], 'atendimentos': list(do_dia)}
        for dia, do_dia in groupby(lista, key=lambda at: at.data)
    ]
