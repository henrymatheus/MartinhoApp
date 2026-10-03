from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = 'agenda'

urlpatterns = [
    path('', views.AgendaDoDiaView.as_view(), name='dia'),
    path('agendamentos/novo/', views.NovoAgendamentoView.as_view(), name='novo'),
    path('agendamentos/<int:pk>/editar/', views.EditarAgendamentoView.as_view(), name='editar'),
    path('historico/', views.BalancoView.as_view(), name='historico'),
    path('historico/exportar/', views.ExportarBalancoView.as_view(), name='exportar_historico'),
    # A tela se chamava "Balanço": links e favoritos antigos continuam funcionando.
    path('balanco/', RedirectView.as_view(pattern_name='agenda:historico', query_string=True)),
    path('balanco/exportar/', RedirectView.as_view(pattern_name='agenda:exportar_historico', query_string=True)),
    path('atendimentos/novo/', views.RegistrarAtendimentoView.as_view(), name='registrar_atendimento'),
    path('ausencias/barbeiro/<int:pk>/marcar/', views.MarcarAusenciaView.as_view(), name='marcar_ausencia'),
    path('ausencias/<int:pk>/desfazer/', views.DesfazerAusenciaView.as_view(), name='desfazer_ausencia'),
    path(
        'agendamentos/<int:pk>/<str:acao>/',
        views.MudarStatusView.as_view(),
        name='mudar_status',
    ),
]
