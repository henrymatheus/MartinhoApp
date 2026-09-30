from django.urls import path

from . import views

app_name = 'agenda'

urlpatterns = [
    path('', views.AgendaDoDiaView.as_view(), name='dia'),
    path('agendamentos/novo/', views.NovoAgendamentoView.as_view(), name='novo'),
    path('agendamentos/<int:pk>/editar/', views.EditarAgendamentoView.as_view(), name='editar'),
    path('ausencias/barbeiro/<int:pk>/marcar/', views.MarcarAusenciaView.as_view(), name='marcar_ausencia'),
    path('ausencias/<int:pk>/desfazer/', views.DesfazerAusenciaView.as_view(), name='desfazer_ausencia'),
    path(
        'agendamentos/<int:pk>/<str:acao>/',
        views.MudarStatusView.as_view(),
        name='mudar_status',
    ),
]
