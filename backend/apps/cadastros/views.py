from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from apps.agenda.models import Agendamento
from apps.contas.models import Usuario
from apps.contas.views import DaBarbeariaMixin

from .forms import BloqueioForm, ClienteForm, SemanaForm
from .models import Barbeiro, Bloqueio, Cliente


class ClientesView(DaBarbeariaMixin, ListView):
    template_name = 'cadastros/clientes.html'
    context_object_name = 'clientes'
    secao = 'clientes'
    paginate_by = 50

    def get_queryset(self):
        clientes = Cliente.objects.filter(barbearia=self.barbearia).order_by('nome')
        busca = self.request.GET.get('q', '').strip()
        if busca:
            # icontains: não diferencia maiúsculas de minúsculas.
            clientes = clientes.filter(Q(nome__icontains=busca) | Q(telefone__icontains=busca))
        return clientes

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['busca'] = self.request.GET.get('q', '').strip()
        return contexto


class ClienteView(DaBarbeariaMixin, DetailView):
    """Ficha do cliente: dados, próximos horários e histórico de atendimentos."""

    template_name = 'cadastros/cliente.html'
    context_object_name = 'cliente'
    secao = 'clientes'

    def get_queryset(self):
        return Cliente.objects.filter(barbearia=self.barbearia)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        cliente = self.object
        contexto['proximos'] = (
            cliente.agendamentos.filter(inicio__gte=timezone.now(), status=Agendamento.Status.AGENDADO)
            .select_related('barbeiro', 'servico')
            .order_by('inicio')
        )
        # prefetch_related busca os itens de todos os atendimentos numa só
        # consulta, em vez de uma consulta por atendimento.
        contexto['atendimentos'] = cliente.atendimentos.select_related('barbeiro').prefetch_related('itens')
        contexto['aniversariante'] = cliente.aniversario_em(timezone.localdate())
        contexto['whatsapp'] = cliente.link_whatsapp()
        return contexto


class FormularioClienteMixin(DaBarbeariaMixin):
    model = Cliente
    form_class = ClienteForm
    template_name = 'cadastros/cliente_form.html'
    secao = 'clientes'

    def get_queryset(self):
        return Cliente.objects.filter(barbearia=self.barbearia)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['barbearia'] = self.barbearia
        return kwargs

    def get_success_url(self):
        return reverse('cadastros:cliente', args=[self.object.pk])


class NovoClienteView(FormularioClienteMixin, CreateView):
    def form_valid(self, form):
        messages.success(self.request, f'{form.instance.nome} cadastrado.')
        return super().form_valid(form)


class EditarClienteView(FormularioClienteMixin, UpdateView):
    def form_valid(self, form):
        messages.success(self.request, 'Dados do cliente atualizados.')
        return super().form_valid(form)


def barbeiros_visiveis(usuario):
    """
    Barbeiros cujos horários o usuário pode editar: um usuário com papel
    "barbeiro" ligado a um barbeiro vê só os próprios; o dono vê todos.
    """
    barbeiros = Barbeiro.objects.filter(barbearia=usuario.barbearia, ativo=True)
    barbeiro_do_usuario = getattr(usuario, 'barbeiro', None)
    if usuario.papel == Usuario.Papel.BARBEIRO and barbeiro_do_usuario is not None:
        return barbeiros.filter(pk=barbeiro_do_usuario.pk)
    return barbeiros


class HorariosView(DaBarbeariaMixin, TemplateView):
    """Lista dos barbeiros com o resumo dos horários e o link da página de agendamento."""

    template_name = 'cadastros/horarios.html'
    secao = 'horarios'

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        barbeiros = list(barbeiros_visiveis(self.request.user).prefetch_related('horarios'))
        if len(barbeiros) == 1 and self.request.user.papel == Usuario.Papel.BARBEIRO:
            contexto['ir_direto'] = barbeiros[0]
        contexto['barbeiros'] = barbeiros
        contexto['link_publico'] = self.request.build_absolute_uri(
            reverse('publico:agendar', args=[self.barbearia.slug])
        )
        return contexto

    def get(self, request, *args, **kwargs):
        contexto = self.get_context_data(**kwargs)
        if 'ir_direto' in contexto:
            return redirect('cadastros:horarios_barbeiro', contexto['ir_direto'].pk)
        return self.render_to_response(contexto)


class HorariosBarbeiroView(DaBarbeariaMixin, TemplateView):
    """Turnos da semana e folgas de um barbeiro."""

    template_name = 'cadastros/horarios_barbeiro.html'
    secao = 'horarios'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.barbearia_id:
            self.barbeiro = get_object_or_404(barbeiros_visiveis(request.user), pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.setdefault('semana', SemanaForm(barbeiro=self.barbeiro))
        contexto.setdefault('folga', BloqueioForm(barbeiro=self.barbeiro))
        contexto['barbeiro'] = self.barbeiro
        contexto['folgas'] = self.barbeiro.bloqueios.filter(data_fim__gte=timezone.localdate())
        return contexto

    def post(self, request, *args, **kwargs):
        if request.POST.get('acao') == 'folga':
            form = BloqueioForm(request.POST, barbeiro=self.barbeiro)
            if form.is_valid():
                form.save()
                messages.success(request, f'Folga registrada: {form.instance}.')
                return redirect(request.path)
            return self.render_to_response(self.get_context_data(folga=form))
        form = SemanaForm(request.POST, barbeiro=self.barbeiro)
        if form.is_valid():
            form.save()
            messages.success(request, f'Horários de {self.barbeiro} salvos.')
            return redirect(request.path)
        return self.render_to_response(self.get_context_data(semana=form))


class RemoverFolgaView(DaBarbeariaMixin, View):
    def post(self, request, pk, folga):
        barbeiro = get_object_or_404(barbeiros_visiveis(request.user), pk=pk)
        get_object_or_404(Bloqueio, pk=folga, barbeiro=barbeiro).delete()
        messages.success(request, 'Folga removida.')
        return redirect('cadastros:horarios_barbeiro', pk)
