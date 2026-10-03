from django.urls import path

from . import views

app_name = 'cadastros'

urlpatterns = [
    path('clientes/', views.ClientesView.as_view(), name='clientes'),
    path('clientes/novo/', views.NovoClienteView.as_view(), name='novo_cliente'),
    path('clientes/<int:pk>/', views.ClienteView.as_view(), name='cliente'),
    path('clientes/<int:pk>/editar/', views.EditarClienteView.as_view(), name='editar_cliente'),
    path('horarios/', views.HorariosView.as_view(), name='horarios'),
    path('horarios/<int:pk>/', views.HorariosBarbeiroView.as_view(), name='horarios_barbeiro'),
    path('horarios/<int:pk>/folgas/<int:folga>/remover/', views.RemoverFolgaView.as_view(), name='remover_folga'),
]
