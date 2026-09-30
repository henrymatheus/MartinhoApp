from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render


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
