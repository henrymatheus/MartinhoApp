from datetime import date, timedelta

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, TemplateView, UpdateView

from apps.contas.views import DaBarbeariaMixin

from .forms import AgendamentoForm
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
        )
        return contexto


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
