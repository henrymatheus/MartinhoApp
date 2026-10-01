"""
Páginas públicas: o agendamento feito pelo próprio cliente, sem login,
e os arquivos do PWA (manifesto, service worker e página offline).
"""

import hashlib
import json
import pathlib
from datetime import date, datetime

from django.contrib.staticfiles import finders
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache

from apps.agenda.disponibilidade import (
    ausente_o_dia_todo,
    dias_com_horario,
    esta_livre,
    horarios_livres,
    proximo_horario,
)
from apps.agenda.models import Agendamento
from apps.cadastros.models import Barbeiro, Servico, encontrar_ou_criar_cliente
from apps.contas.models import Barbearia
from apps.contas.notificacoes import notificar_novo_agendamento
from apps.contas.telefones import mesmo_telefone

from .forms import ConfirmarAgendamentoForm

# Um mesmo telefone pode ter no máximo este número de horários futuros
# marcados pela página pública. Evita que alguém ocupe a agenda inteira.
MAXIMO_POR_TELEFONE = 3
SALT_CONFIRMACAO = 'agendamento-publico'


def barbearia_publica(slug):
    return get_object_or_404(Barbearia, slug=slug, agendamento_online=True)


def cartoes_de_barbeiros(barbeiros, servicos):
    """
    Primeira tela do cliente: cada barbeiro com a situação de hoje e o próximo
    horário livre. Como o serviço ainda não foi escolhido, o "próximo horário"
    usa o serviço mais curto da barbearia. Quem tem horário vem primeiro.
    """
    hoje = timezone.localdate()
    referencia = min(servicos, key=lambda s: s.duracao_minutos) if servicos else None
    cartoes = []
    for barbeiro in barbeiros:
        dias_com_turno = {h.dia_semana for h in barbeiro.horarios.all()}
        if ausente_o_dia_todo(barbeiro, hoje):
            situacao = 'Ausente hoje'
        elif hoje.weekday() in dias_com_turno:
            situacao = 'Atendendo hoje'
        else:
            situacao = 'Não atende hoje'
        proximo = proximo_horario(barbeiro, referencia) if referencia else None
        tem_hoje = proximo is not None and timezone.localdate(proximo) == hoje
        if situacao == 'Atendendo hoje' and not tem_hoje:
            situacao = 'Sem horários livres hoje'
        cartoes.append({'barbeiro': barbeiro, 'situacao': situacao, 'proximo': proximo, 'hoje': tem_hoje})
    return sorted(cartoes, key=lambda c: (c['proximo'] is None, c['proximo'] or timezone.now()))


def ler_escolhas(barbearia, dados):
    """
    Interpreta o que o cliente já escolheu e calcula as opções do próximo passo.

    Fluxo: barbeiro (com a situação e o próximo horário livre de cada um) ->
    serviço -> agenda daquele barbeiro (dias e horários livres) -> dados.

    O link /agendar/<barbearia>/?barbeiro=3 já abre com o barbeiro escolhido,
    para cada um divulgar o seu. Uma escolha inválida é ignorada, e o cliente
    volta ao passo correspondente.
    """
    servicos = list(Servico.objects.filter(barbearia=barbearia, ativo=True))
    # Só barbeiros com algum horário cadastrado aparecem para o cliente.
    barbeiros = list(
        Barbeiro.objects.filter(barbearia=barbearia, ativo=True, horarios__isnull=False)
        .distinct()
        .prefetch_related('horarios')
    )

    e = {'servicos': servicos, 'barbeiro': None, 'servico': None, 'cartoes': [], 'dias': [], 'dia': None,
         'horarios': [], 'inicio': None}
    e['barbeiro'] = next((b for b in barbeiros if str(b.pk) == dados.get('barbeiro')), None)
    if not e['barbeiro']:
        e['cartoes'] = cartoes_de_barbeiros(barbeiros, servicos)
        return e

    e['servico'] = next((s for s in servicos if str(s.pk) == dados.get('servico')), None)
    if not e['servico']:
        return e

    e['dias'] = dias_com_horario(e['barbeiro'], e['servico'])
    try:
        pedido = date.fromisoformat(dados.get('data', ''))
    except ValueError:
        pedido = None
    # Sem dia escolhido (ou com um dia que não tem mais horário), a agenda
    # abre no primeiro dia com horário livre.
    e['dia'] = pedido if pedido in e['dias'] else (e['dias'][0] if e['dias'] else None)
    if not e['dia']:
        return e

    e['horarios'] = horarios_livres(e['barbeiro'], e['servico'], e['dia'])
    # O horário só vale para o dia que o cliente escolheu. Se aquele dia não
    # está mais disponível, o horário é descartado, para nunca agendar num
    # dia diferente do que o cliente viu.
    if e['dia'] == pedido:
        hora = dados.get('hora', '')
        e['inicio'] = next((h for h in e['horarios'] if timezone.localtime(h).strftime('%H:%M') == hora), None)
    return e


# never_cache: os horários livres mudam o tempo todo (o barbeiro cadastra a
# agenda, outro cliente marca). A resposta vai com "Cache-Control: no-store",
# para o navegador e o app instalado nunca mostrarem uma cópia guardada.
@method_decorator(never_cache, name='dispatch')
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
                # O aviso ao barbeiro só sai depois que a gravação for
                # confirmada no banco (on_commit). Se ele falhar, o
                # agendamento continua valendo.
                transaction.on_commit(lambda: notificar_novo_agendamento(agendamento))
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


# Arquivos que o service worker guarda no aparelho (lista ESSENCIAIS do sw.js).
GUARDADOS_NO_APARELHO = ('css/tokens.css', 'css/martinho.css', 'img/martinho-simbolo.svg')


def versao_dos_arquivos():
    """
    Uma "impressão digital" do conteúdo dos arquivos guardados no aparelho.

    O service worker guarda o CSS no celular e só busca de novo quando a
    versão muda. Com uma versão fixa, uma mudança no CSS nunca chegava a
    quem já tinha aberto o sistema (a página vinha nova, o estilo velho).
    Calculada pelo conteúdo, a versão muda sozinha a cada alteração.
    """
    impressao = hashlib.sha256()
    for caminho in GUARDADOS_NO_APARELHO:
        arquivo = finders.find(caminho)
        if arquivo:
            impressao.update(pathlib.Path(arquivo).read_bytes())
    return impressao.hexdigest()[:12]


def service_worker(request):
    # Servido na raiz (/sw.js) para poder atender todas as páginas do site.
    resposta = render(request, 'publico/sw.js', {'versao': versao_dos_arquivos()}, content_type='application/javascript')
    resposta['Cache-Control'] = 'no-cache'
    return resposta


def offline(request):
    return render(request, 'publico/offline.html')
