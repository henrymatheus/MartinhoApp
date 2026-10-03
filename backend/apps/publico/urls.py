from django.urls import path

from . import views

app_name = 'publico'

urlpatterns = [
    path('agendar/<slug:slug>/', views.AgendarView.as_view(), name='agendar'),
    path('agendar/<slug:slug>/confirmado/<str:token>/', views.ConfirmadoView.as_view(), name='confirmado'),
    path('agendar/<slug:slug>/manifest.webmanifest', views.manifesto_barbearia, name='manifesto_barbearia'),
    path('manifest.webmanifest', views.manifesto_sistema, name='manifesto'),
    path('sw.js', views.service_worker, name='service_worker'),
    path('offline/', views.offline, name='offline'),
]
