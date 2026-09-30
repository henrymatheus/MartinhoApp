from datetime import date, time, timedelta

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, TemplateView, UpdateView

from apps.cadastros.models import Barbeiro, Bloqueio
from apps.cadastros.views import barbeiros_visiveis
from apps.contas.views import DaBarbeariaMixin

from .disponibilidade import ausente_em, sobrepoe
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
