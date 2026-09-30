import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View

from .models import InscricaoPush


class DaBarbeariaMixin(LoginRequiredMixin):
    """
    Base de todas as telas do sistema.

    - Quem não está logado vai para a tela de login (LoginRequiredMixin).
    - Quem está logado mas não pertence a nenhuma barbearia vê um aviso.
    - `self.barbearia` é a barbearia do usuário: toda consulta das telas
      filtra por ela, e assim uma barbearia nunca vê dados de outra.
    - `secao` marca o item ativo no menu do topo.
    """

    secao = None

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.barbearia_id is None:
            return render(request, 'contas/sem_barbearia.html', status=403)
        return super().dispatch(request, *args, **kwargs)

    @property
    def barbearia(self):
        return self.request.user.barbearia

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['secao'] = self.secao
        return contexto


class InscricaoPushView(LoginRequiredMixin, View):
    """
    Recebe do navegador os dados da inscrição em avisos (POST com JSON) e
    guarda para o usuário logado. DELETE cancela a inscrição do aparelho.
    """

    def post(self, request):
        try:
            dados = json.loads(request.body)
            endpoint = dados['endpoint']
            chaves = dados['keys']
            p256dh, auth = chaves['p256dh'], chaves['auth']
        except (ValueError, KeyError, TypeError):
            return JsonResponse({'erro': 'Inscrição inválida.'}, status=400)
        if not endpoint.startswith('https://'):
            return JsonResponse({'erro': 'Inscrição inválida.'}, status=400)
        InscricaoPush.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                'usuario': request.user,
                'p256dh': p256dh,
                'auth': auth,
                'navegador': request.headers.get('User-Agent', '')[:200],
            },
        )
        return JsonResponse({'ok': True})

    def delete(self, request):
        try:
            endpoint = json.loads(request.body)['endpoint']
        except (ValueError, KeyError, TypeError):
            return JsonResponse({'erro': 'Inscrição inválida.'}, status=400)
        InscricaoPush.objects.filter(endpoint=endpoint, usuario=request.user).delete()
        return JsonResponse({'ok': True})
