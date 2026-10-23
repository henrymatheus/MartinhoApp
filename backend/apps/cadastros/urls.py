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
    path('servicos/', views.ServicosView.as_view(), name='servicos'),
    path('servicos/novo/', views.NovoServicoView.as_view(), name='novo_servico'),
    path('servicos/<int:pk>/editar/', views.EditarServicoView.as_view(), name='editar_servico'),
    path('parceiros/', views.ParceirosView.as_view(), name='parceiros'),
    path('parceiros/novo/', views.NovoParceiroView.as_view(), name='novo_parceiro'),
    path('parceiros/<int:pk>/editar/', views.EditarParceiroView.as_view(), name='editar_parceiro'),
    path('parceiros/<int:pk>/remover/', views.RemoverParceiroView.as_view(), name='remover_parceiro'),
]
