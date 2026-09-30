"""
Páginas públicas: o agendamento feito pelo próprio cliente, sem login,
e os arquivos do PWA (manifesto, service worker e página offline).
"""

import json
from datetime import date, datetime

from django.contrib.staticfiles.storage import staticfiles_storage
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View

from apps.agenda.disponibilidade import dias_de_atendimento, esta_livre, horarios_livres
from apps.agenda.models import Agendamento
from apps.cadastros.models import Barbeiro, Cliente, Servico
from apps.contas.models import Barbearia
from apps.contas.telefones import mesmo_telefone, somente_digitos

from .forms import ConfirmarAgendamentoForm

# Um mesmo telefone pode ter no máximo este número de horários futuros
# marcados pela página pública. Evita que alguém ocupe a agenda inteira.
MAXIMO_POR_TELEFONE = 3
SALT_CONFIRMACAO = 'agendamento-publico'


def barbearia_publica(slug):
    return get_object_or_404(Barbearia, slug=slug, agendamento_online=True)


def ler_escolhas(barbearia, dados):
    """
    Interpreta o que o cliente já escolheu (serviço, barbeiro, dia, hora) e
    calcula as opções do próximo passo. Uma escolha inválida é ignorada, e
    o cliente volta ao passo correspondente.
    """
    servicos = list(Servico.objects.filter(barbearia=barbearia, ativo=True))
    # Só barbeiros com algum horário cadastrado aparecem para o cliente.
    barbeiros = list(Barbeiro.objects.filter(barbearia=barbearia, ativo=True, horarios__isnull=False).distinct())

    e = {'servicos': servicos, 'barbeiros': barbeiros, 'servico': None, 'barbeiro': None,
         'dias': [], 'dia': None, 'horarios': [], 'inicio': None}
    e['servico'] = next((s for s in servicos if str(s.pk) == dados.get('servico')), None)
    if e['servico']:
        e['barbeiro'] = next((b for b in barbeiros if str(b.pk) == dados.get('barbeiro')), None)
    if e['barbeiro']:
        e['dias'] = dias_de_atendimento(e['barbeiro'])
        try:
            dia = date.fromisoformat(dados.get('data', ''))
        except ValueError:
            dia = None
        if dia in e['dias']:
            e['dia'] = dia
            e['horarios'] = horarios_livres(e['barbeiro'], e['servico'], dia)
            hora = dados.get('hora', '')
            e['inicio'] = next((h for h in e['horarios'] if timezone.localtime(h).strftime('%H:%M') == hora), None)
    return e


def encontrar_ou_criar_cliente(barbearia, nome, telefone):
    """
    Quem já é cliente é reconhecido pelo telefone, e o agendamento vai para a
    ficha existente, com o histórico. Um telefone novo cria um cliente novo.
    """
    candidatos = Cliente.objects.filter(barbearia=barbearia, telefone__contains=somente_digitos(telefone)[-4:])
    for cliente in candidatos:
        if mesmo_telefone(cliente.telefone, telefone):
            return cliente
    return Cliente.objects.create(barbearia=barbearia, nome=nome, telefone=telefone)


class AgendarView(View):
    template_name = 'publico/agendar.html'

    def get(self, request, slug):
        barbearia = barbearia_publica(slug)
        escolhas = ler_escolhas(barbearia, request.GET)
        return self.mostrar(request, barbearia, escolhas, ConfirmarAgendamentoForm())

    def post(self, request, slug):
        barbearia = barbearia_publica(slug)
        escolhas = ler_escolhas(barbearia, request.POST)
        form = ConfirmarAgendamentoForm(request.POST)
        if not escolhas['inicio']:
            form.add_error(None, 'Esse horário não está mais disponível. Escolha outro, por favor.')
            return self.mostrar(request, barbearia, escolhas, form)
        if not form.is_valid():
            return self.mostrar(request, barbearia, escolhas, form)
        if form.eh_robo():
            return redirect(request.path)

        telefone = form.cleaned_data['telefone']
        futuros = Agendamento.objects.filter(
            barbearia=barbearia, status=Agendamento.Status.AGENDADO, inicio__gte=timezone.now()
        ).select_related('cliente')
        if sum(mesmo_telefone(ag.cliente.telefone, telefone) for ag in futuros) >= MAXIMO_POR_TELEFONE:
            form.add_error(
                None,
                f'Este telefone já tem {MAXIMO_POR_TELEFONE} horários marcados. Para marcar mais, fale com a barbearia.',
            )
            return self.mostrar(request, barbearia, escolhas, form)

        try:
            # Tudo ou nada: se o horário for ocupado no último instante, o
            # cliente novo também não é gravado.
            with transaction.atomic():
                # Confere de novo dentro da transação: entre abrir a página e
                # confirmar, outra pessoa pode ter pego o horário.
                if not esta_livre(escolhas['barbeiro'], escolhas['servico'], escolhas['inicio']):
                    raise ValidationError('ocupado')
                cliente = encontrar_ou_criar_cliente(barbearia, form.cleaned_data['nome'], telefone)
                agendamento = Agendamento(
                    barbearia=barbearia,
                    cliente=cliente,
                    barbeiro=escolhas['barbeiro'],
                    servico=escolhas['servico'],
                    inicio=escolhas['inicio'],
                    observacoes='Agendado pelo cliente na página online.',
                )
                agendamento.save()  # o save() trava o barbeiro e verifica conflito
        except ValidationError:
            form.add_error(None, 'Esse horário acabou de ser ocupado. Escolha outro, por favor.')
            return self.mostrar(request, barbearia, ler_escolhas(barbearia, request.POST), form)

        token = signing.dumps(agendamento.pk, salt=SALT_CONFIRMACAO)
        return redirect('publico:confirmado', slug=barbearia.slug, token=token)

    def mostrar(self, request, barbearia, escolhas, form):
        return render(request, self.template_name, {'barbearia': barbearia, 'e': escolhas, 'form': form})


class ConfirmadoView(View):
    """
    Página de confirmação. O endereço leva um código assinado pelo Django
    (signing), e não o número do agendamento: assim ninguém consegue ver o
    horário de outra pessoa trocando o número na barra de endereço.
    """

    def get(self, request, slug, token):
        barbearia = barbearia_publica(slug)
        try:
            pk = signing.loads(token, salt=SALT_CONFIRMACAO, max_age=60 * 60 * 24 * 60)
        except signing.BadSignature:
            raise Http404
        agendamento = get_object_or_404(
            Agendamento.objects.select_related('cliente', 'barbeiro', 'servico'), pk=pk, barbearia=barbearia
        )
        inicio = timezone.localtime(agendamento.inicio)
        mensagem = (
            f'Olá! Sou {agendamento.cliente.nome} e agendei {agendamento.servico.nome.lower()} '
            f'com {agendamento.barbeiro.nome} em {inicio:%d/%m} às {inicio:%H:%M}.'
        )
        return render(request, 'publico/confirmado.html', {
            'barbearia': barbearia,
            'ag': agendamento,
            'whatsapp_barbearia': barbearia.link_whatsapp(mensagem),
        })


# ---------- PWA ----------

def manifesto(nome, nome_curto, inicio, cor):
    """O arquivo que o celular lê para instalar o site como app."""

    def icone(arquivo, tamanho, finalidade='any'):
        return {
            'src': staticfiles_storage.url(f'img/{arquivo}'),
            'sizes': tamanho,
            'type': 'image/png',
            'purpose': finalidade,
        }

    dados = {
        'name': nome,
        'short_name': nome_curto,
        'lang': 'pt-BR',
        'start_url': inicio,
        'scope': inicio,
        'display': 'standalone',
        'background_color': cor,
        'theme_color': cor,
        'icons': [
            icone('icone-192.png', '192x192'),
            icone('icone-512.png', '512x512'),
            icone('icone-512.png', '512x512', 'maskable'),
        ],
    }
    return HttpResponse(json.dumps(dados, ensure_ascii=False), content_type='application/manifest+json')


def manifesto_sistema(request):
    return manifesto('Martinho', 'Martinho', '/', '#0e2240')


def manifesto_barbearia(request, slug):
    barbearia = barbearia_publica(slug)
    return manifesto(f'Agendar · {barbearia.nome}', barbearia.nome[:12], reverse('publico:agendar', args=[slug]), '#0e2240')


def service_worker(request):
    # Servido na raiz (/sw.js) para poder atender todas as páginas do site.
    resposta = render(request, 'publico/sw.js', {'versao': 'v1'}, content_type='application/javascript')
    resposta['Cache-Control'] = 'no-cache'
    return resposta


def offline(request):
    return render(request, 'publico/offline.html')
