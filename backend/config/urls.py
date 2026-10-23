from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

# Textos do admin: aparecem no título da aba, no cabeçalho e na tela inicial.
admin.site.site_header = 'Martinho'
admin.site.site_title = 'Martinho'
admin.site.index_title = 'Administração'

urlpatterns = [
    # O sistema: a agenda é a página inicial.
    path('', include('apps.agenda.urls')),
    path('', include('apps.cadastros.urls')),
    path('', include('apps.contas.urls')),
    # Páginas públicas (sem login): agendamento do cliente e arquivos do PWA.
    path('', include('apps.publico.urls')),
    # Login e logout prontos do Django, com o template da marca.
    path('entrar/', auth_views.LoginView.as_view(redirect_authenticated_user=True), name='entrar'),
    path('sair/', auth_views.LogoutView.as_view(), name='sair'),
    # Área administrativa: cadastros de barbearias, usuários, serviços etc.
    path('admin/', admin.site.urls),
]

# Na sua máquina (DEBUG ligado), o próprio Django serve as logos enviadas,
# da pasta media/. Em produção isso não roda: as logos vêm do Supabase.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
