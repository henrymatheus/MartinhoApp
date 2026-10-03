import csv
from datetime import date, time, timedelta
from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, FormView, TemplateView, UpdateView

from apps.cadastros.models import Barbeiro, Bloqueio
from apps.cadastros.views import barbeiros_visiveis
from apps.contas.models import Usuario
from apps.contas.views import DaBarbeariaMixin

from .balanco import Periodo, atendimentos_do_periodo, barbeiros_do_balanco, calcular, lista_detalhada, mes_anterior
from .disponibilidade import ausente_em, sobrepoe
from .forms import AgendamentoForm, AtendimentoAvulsoForm
from .models import Agendamento


def ler_data(texto):
    try:
        return date.fromisoformat(texto)
    except (TypeError, ValueError):
        return timezone.localdate()


def url_do_dia(dia):
    return f"{reverse('agenda:dia')}?data={dia.isoformat()}"


class AgendaDoDiaView(DaBarbeariaMixin, TemplateView):
    """A agenda de um dia (hoje, se nenhum for escolhido), em ordem de horário."""

    template_name = 'agenda/dia.html'
    secao = 'agenda'

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        dia = ler_data(self.request.GET.get('data'))
        hoje = timezone.localdate()
        agora = timezone.now()

        # inicio__date usa o fuso de São Paulo (TIME_ZONE), então um horário às
        # 23:30 fica no dia certo mesmo sendo gravado em UTC.
        agendamentos = list(
            Agendamento.objects.filter(barbearia=self.barbearia, inicio__date=dia)
            .select_related('cliente', 'barbeiro', 'servico', 'barbearia')
            .order_by('inicio')
        )
        for ag in agendamentos:
            ag.aniversariante = ag.cliente.aniversario_em(dia)
            ag.whatsapp = ag.cliente.link_whatsapp(ag.mensagem_lembrete())
            # Horário marcado com um barbeiro que ficou ausente: destacado na
            # agenda, com a mensagem pronta para avisar o cliente.
            ag.barbeiro_ausente = ag.status == Agendamento.Status.AGENDADO and ausente_em(
                ag.barbeiro, ag.inicio, ag.fim
            )
            if ag.barbeiro_ausente:
                ag.whatsapp_ausencia = ag.cliente.link_whatsapp(ag.mensagem_ausencia())

        # A linha dourada "agora" vai antes do primeiro horário que ainda não
        # terminou. Só aparece na agenda de hoje.
        agora_antes_de = None
        if dia == hoje:
            agora_antes_de = next((ag.pk for ag in agendamentos if ag.fim > agora), 'fim')

        contexto.update(
            dia=dia,
            eh_hoje=dia == hoje,
            anterior=dia - timedelta(days=1),
            proximo=dia + timedelta(days=1),
            hoje=hoje,
            agendamentos=agendamentos,
            agora_antes_de=agora_antes_de,
            total_ativos=sum(1 for ag in agendamentos if ag.status == Agendamento.Status.AGENDADO),
            equipe=self.equipe_do_dia(dia),
            pode_marcar_ausencia=dia >= hoje,
        )
        if not agendamentos:
            # Dia vazio: mostra os próximos horários marcados, para ninguém
            # achar que um agendamento sumiu só porque está em outro dia.
            contexto['proximos'] = (
                Agendamento.objects.filter(
                    barbearia=self.barbearia, status=Agendamento.Status.AGENDADO, inicio__gte=agora
                )
                .select_related('cliente', 'barbeiro', 'servico')
                .order_by('inicio')[:5]
            )
        return contexto


    def equipe_do_dia(self, dia):
        """
        Situação de cada barbeiro no dia: atendendo, ausente (dia inteiro ou
        parte) ou sem expediente. Usado na faixa "Equipe do dia" da agenda.
        """
        editaveis = set(barbeiros_visiveis(self.request.user).values_list('pk', flat=True))
        equipe = []
        barbeiros = Barbeiro.objects.filter(barbearia=self.barbearia, ativo=True).prefetch_related('horarios')
        for barbeiro in barbeiros:
            turnos = [t for t in barbeiro.horarios.all() if t.dia_semana == dia.weekday()]
            ausencias = list(barbeiro.bloqueios.filter(data_inicio__lte=dia, data_fim__gte=dia))
            dia_inteiro = next((a for a in ausencias if not a.dia_parcial), None)
            parciais = [a for a in ausencias if a.dia_parcial]
            if dia_inteiro:
                situacao, texto = 'ausente', 'Ausente'
                if dia_inteiro.data_fim > dia:
                    texto = f'Ausente até {dia_inteiro.data_fim:%d/%m}'
                if dia_inteiro.motivo:
                    texto += f' · {dia_inteiro.motivo}'
            elif not turnos:
                situacao, texto = 'folga', 'Não atende neste dia'
            else:
                situacao = 'parcial' if parciais else 'atendendo'
                texto = ', '.join(f'{t.inicio:%H:%M}–{t.fim:%H:%M}' for t in turnos)
                if parciais:
                    texto += ' · ausente ' + ', '.join(f'{a.hora_inicio:%H:%M}–{a.hora_fim:%H:%M}' for a in parciais)
            equipe.append({
                'barbeiro': barbeiro,
                'situacao': situacao,
                'texto': texto,
                'pode_editar': barbeiro.pk in editaveis,
                # Só ausências deste único dia podem ser desfeitas aqui; férias
                # de vários dias se editam na tela Horários.
                'desfazer': [a for a in ausencias if a.data_inicio == a.data_fim == dia],
            })
        return equipe


def texto_afetados(barbeiro, afetados):
    texto = f'Ausência de {barbeiro} registrada. Os clientes não conseguem mais agendar com ele nesse período.'
    if len(afetados) == 1:
        texto += ' Atenção: 1 horário já marcado com ele está destacado abaixo.'
    elif afetados:
        texto += f' Atenção: {len(afetados)} horários já marcados com ele estão destacados abaixo.'
    return texto


class MarcarAusenciaView(DaBarbeariaMixin, View):
    """
    "Faltou" ou "Saiu agora", direto da agenda. Cria uma ausência (Bloqueio)
    para o dia: inteira, ou a partir do horário atual.
    """

    def post(self, request, pk):
        barbeiro = get_object_or_404(barbeiros_visiveis(request.user), pk=pk)
        dia = ler_data(request.POST.get('data'))
        hoje = timezone.localdate()
        if dia < hoje:
            messages.error(request, 'Não dá para marcar ausência em um dia que já passou.')
            return redirect(url_do_dia(dia))

        ausencia = Bloqueio(barbeiro=barbeiro, data_inicio=dia, data_fim=dia, motivo='Falta')
        if request.POST.get('modo') == 'agora' and dia == hoje:
            agora = timezone.localtime().time().replace(second=0, microsecond=0)
            if agora >= time(23, 59):
                messages.error(request, 'O dia já está terminando.')
                return redirect(url_do_dia(dia))
            ausencia.hora_inicio, ausencia.hora_fim, ausencia.motivo = agora, time(23, 59), 'Saiu mais cedo'
        ausencia.save()

        inicio, fim = ausencia.intervalo_em(dia)
        afetados = [
            ag
            for ag in Agendamento.objects.filter(barbeiro=barbeiro, inicio__date=dia, status=Agendamento.Status.AGENDADO)
            if sobrepoe(ag.inicio, ag.fim, inicio, fim)
        ]
        (messages.warning if afetados else messages.success)(request, texto_afetados(barbeiro, afetados))
        return redirect(url_do_dia(dia))


class DesfazerAusenciaView(DaBarbeariaMixin, View):
    def post(self, request, pk):
        ausencia = get_object_or_404(Bloqueio, pk=pk, barbeiro__in=barbeiros_visiveis(request.user))
        dia = ausencia.data_inicio
        ausencia.delete()
        messages.success(request, f'Ausência de {ausencia.barbeiro} desfeita.')
        return redirect(url_do_dia(dia))


class FormularioAgendamentoMixin(DaBarbeariaMixin):
    """O que a tela de novo agendamento e a de edição têm em comum."""

    model = Agendamento
    form_class = AgendamentoForm
    template_name = 'agenda/form.html'
    secao = 'agenda'

    def get_queryset(self):
        return Agendamento.objects.filter(barbearia=self.barbearia)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['barbearia'] = self.barbearia
        return kwargs

    def get_success_url(self):
        return url_do_dia(timezone.localdate(self.object.inicio))


class NovoAgendamentoView(FormularioAgendamentoMixin, CreateView):
    def get_initial(self):
        # A partir da agenda de um dia, o formulário já vem com aquela data.
        # A partir da ficha de um cliente, já vem com o cliente escolhido.
        inicial = super().get_initial()
        inicial['data'] = ler_data(self.request.GET.get('data'))
        if self.request.GET.get('cliente'):
            inicial['cliente'] = self.request.GET['cliente']
        return inicial

    def form_valid(self, form):
        resposta = super().form_valid(form)
        inicio = timezone.localtime(self.object.inicio)
        messages.success(self.request, f'Agendado: {self.object.cliente} às {inicio:%H:%M} de {inicio:%d/%m}.')
        return resposta


class EditarAgendamentoView(FormularioAgendamentoMixin, UpdateView):
    def form_valid(self, form):
        messages.success(self.request, 'Agendamento atualizado.')
        return super().form_valid(form)


class MudarStatusView(DaBarbeariaMixin, View):
    """Botões Concluir, Cancelar e Faltou do cartão da agenda (sempre por POST)."""

    def post(self, request, pk, acao):
        if acao not in ('concluir', 'cancelar', 'faltou'):
            raise Http404
        ag = get_object_or_404(Agendamento, pk=pk, barbearia=self.barbearia)
        if ag.status != Agendamento.Status.AGENDADO:
            messages.error(request, f'Este agendamento já está como "{ag.get_status_display()}".')
            return redirect(url_do_dia(timezone.localdate(ag.inicio)))
        try:
            if acao == 'concluir':
                ag.concluir()
                messages.success(request, f'Atendimento de {ag.cliente} concluído e registrado no histórico.')
            elif acao == 'cancelar':
                ag.status = Agendamento.Status.CANCELADO
                ag.save()
                messages.success(request, f'Agendamento de {ag.cliente} cancelado. O horário ficou livre.')
            else:
                ag.status = Agendamento.Status.FALTOU
                ag.save()
                messages.success(request, f'{ag.cliente} marcado como falta.')
        except ValidationError as erro:
            messages.error(request, ' '.join(erro.messages))
        return redirect(url_do_dia(timezone.localdate(ag.inicio)))


class EscopoDoBalancoMixin(DaBarbeariaMixin):
    """
    Decide de quem é o histórico que a tela mostra.

    O barbeiro sempre vê o próprio: o ?barbeiro= da URL é ignorado para ele,
    então não adianta trocar o número para ver o de um colega. O dono vê
    todos juntos ou escolhe um barbeiro.
    """

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.barbearia_id:
            self.permitidos = barbeiros_do_balanco(request.user)
            self.eh_barbeiro = request.user.papel == Usuario.Papel.BARBEIRO
            self.barbeiro = None
            if self.eh_barbeiro:
                self.barbeiro = self.permitidos.first()
            elif request.GET.get('barbeiro', '').isdigit():
                self.barbeiro = get_object_or_404(self.permitidos, pk=request.GET['barbeiro'])
        return super().dispatch(request, *args, **kwargs)

    @property
    def sem_vinculo(self):
        """Login com papel barbeiro que não está ligado a uma ficha de barbeiro."""
        return self.eh_barbeiro and self.barbeiro is None

    def url_com(self, nome_url, periodo, barbeiro=None):
        parametros = periodo.parametros()
        barbeiro = barbeiro or self.barbeiro
        if barbeiro is not None and not self.eh_barbeiro:
            parametros['barbeiro'] = barbeiro.pk
        return f'{reverse(nome_url)}?{urlencode(parametros)}'


class BalancoView(EscopoDoBalancoMixin, TemplateView):
    """
    Histórico de atendimentos do período (a antiga tela "Balanço"):
    quantidade e faturamento, gráfico por dia, comparação com o período
    anterior, estatísticas, volume e valor de cada serviço, resumo por
    barbeiro (para o dono) e a lista de atendimentos dia a dia.
    """

    template_name = 'agenda/balanco.html'
    secao = 'historico'

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        hoje = timezone.localdate()
        periodo = Periodo.da_requisicao(self.request.GET, hoje)
        contexto.update(
            periodo=periodo,
            hoje=hoje,
            eh_barbeiro=self.eh_barbeiro,
            barbeiro=self.barbeiro,
            barbeiros=self.permitidos,
            atalhos=self.atalhos(periodo, hoje),
            url_anterior=self.url_com('agenda:historico', periodo.deslocar(-1)),
            url_proximo=self.url_com('agenda:historico', periodo.deslocar(1)),
            # Não há atendimento no futuro: a seta "próximo" para no período atual.
            tem_proximo=periodo.fim < hoje,
            url_exportar=self.url_com('agenda:exportar_historico', periodo),
        )
        if self.sem_vinculo:
            # Não há o que mostrar; a tela explica o que fazer.
            contexto['sem_vinculo'] = True
            return contexto
        resultado = calcular(self.barbearia, periodo, hoje, self.barbeiro)
        if resultado['grafico']:
            # Tocar numa barra abre o histórico daquele dia (ou mês).
            for barra in resultado['grafico']['barras']:
                barra['url'] = self.url_com('agenda:historico', barra['periodo'])
        for linha in resultado['por_barbeiro']:
            # Na tabela do dono, tocar no barbeiro abre o histórico só dele.
            if linha['barbeiro_id']:
                linha['url'] = f"{reverse('agenda:historico')}?{urlencode({**periodo.parametros(), 'barbeiro': linha['barbeiro_id']})}"
        contexto.update(resultado)
        return contexto

    def atalhos(self, periodo, hoje):
        """Botões de um toque para os períodos mais usados."""
        opcoes = [
            ('Hoje', Periodo.do_tipo('dia', hoje)),
            ('Esta semana', Periodo.do_tipo('semana', hoje)),
            ('Este mês', Periodo.do_tipo('mes', hoje)),
            ('Mês passado', Periodo.do_tipo('mes', mes_anterior(hoje))),
        ]
        return [
            {'texto': texto, 'url': self.url_com('agenda:historico', p), 'ativo': p == periodo}
            for texto, p in opcoes
        ]


def celula_segura(texto):
    """
    Evita que um nome como "=HIPERLINK(...)" vire fórmula ao abrir no Excel.
    O nome do cliente pode vir da página pública, digitado por qualquer um.
    """
    texto = str(texto)
    return "'" + texto if texto[:1] in ('=', '+', '-', '@') else texto


class ExportarBalancoView(EscopoDoBalancoMixin, View):
    """
    O período em CSV, com a mesma regra de acesso da tela. Ponto e vírgula,
    no padrão do Excel em português; o BOM no início do arquivo faz o Excel
    ler os acentos corretamente.
    """

    def get(self, request):
        if self.sem_vinculo:
            raise Http404
        periodo = Periodo.da_requisicao(request.GET, timezone.localdate())
        atendimentos = lista_detalhada(atendimentos_do_periodo(self.barbearia, periodo, self.barbeiro))
        nome = f'historico-{periodo.inicio:%Y-%m-%d}-a-{periodo.fim:%Y-%m-%d}.csv'
        resposta = HttpResponse(content_type='text/csv; charset=utf-8')
        resposta['Content-Disposition'] = f'attachment; filename="{nome}"'
        resposta.write('﻿')
        planilha = csv.writer(resposta, delimiter=';')
        planilha.writerow(['Data', 'Horário', 'Cliente', 'Barbeiro', 'Serviços', 'Valor', 'Observações'])
        # Na tela, o dia mais recente vem primeiro; na planilha, a ordem
        # cronológica é mais útil.
        for at in sorted(atendimentos, key=lambda a: a.data):
            inicio = at.agendamento.inicio if at.agendamento else None
            planilha.writerow([
                f'{at.data:%d/%m/%Y}',
                f'{timezone.localtime(inicio):%H:%M}' if inicio else 'sem horário',
                celula_segura(at.cliente),
                celula_segura(at.barbeiro or '—'),
                celula_segura(', '.join(item.descricao for item in at.itens.all())),
                # Número com vírgula e sem "R$", para o Excel somar a coluna.
                f'{at.total:.2f}'.replace('.', ','),
                celula_segura(at.observacoes),
            ])
        return resposta


class RegistrarAtendimentoView(EscopoDoBalancoMixin, FormView):
    """Atendimento de quem chegou sem hora marcada: vai direto para a ficha do cliente e o histórico."""

    template_name = 'agenda/registrar_atendimento.html'
    form_class = AtendimentoAvulsoForm
    secao = 'historico'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # O dono registra para qualquer barbeiro ativo; o barbeiro, só para si.
        barbeiros = self.permitidos if self.eh_barbeiro else self.permitidos.filter(ativo=True)
        kwargs.update(barbearia=self.barbearia, barbeiros=barbeiros)
        return kwargs

    def get_initial(self):
        # A partir da ficha de um cliente, o formulário já vem com ele escolhido.
        inicial = super().get_initial()
        if self.request.GET.get('cliente'):
            inicial['cliente'] = self.request.GET['cliente']
        return inicial

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['sem_vinculo'] = self.sem_vinculo
        return contexto

    def form_valid(self, form):
        atendimento = form.save()
        messages.success(self.request, f'Atendimento de {atendimento.cliente} registrado.')
        # Volta para o histórico do dia do atendimento, onde ele já aparece.
        return redirect(self.url_com('agenda:historico', Periodo.do_tipo('dia', atendimento.data), atendimento.barbeiro))
