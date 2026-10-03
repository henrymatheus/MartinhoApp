from django.urls import path

from . import views

app_name = 'contas'

urlpatterns = [
    path('avisos/inscricao/', views.InscricaoPushView.as_view(), name='inscricao_push'),
]
