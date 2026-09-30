from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Barbearia, InscricaoPush, Usuario


class DaBarbeariaAdmin(admin.ModelAdmin):
    """
    Base do admin para models que pertencem a uma barbearia.

    O superusuário vê tudo e escolhe a barbearia em cada registro.
    Qualquer outro usuário vê só a própria barbearia, e o campo
    `barbearia` é preenchido automaticamente.
    """

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(barbearia=request.user.barbearia)

    def get_exclude(self, request, obj=None):
        exclude = list(super().get_exclude(request, obj) or [])
        if not request.user.is_superuser:
            exclude.append('barbearia')
        return exclude

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if request.user.is_superuser:
            return form
        barbearia = request.user.barbearia

        # A barbearia é definida antes da validação, porque o clean() do model
        # confere se cliente, barbeiro e serviço são da mesma barbearia.
        class FormDaBarbearia(form):
            def __init__(self, *args, **kw):
                super().__init__(*args, **kw)
                self.instance.barbearia = barbearia

        return FormDaBarbearia

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Nas listas de escolha (cliente, barbeiro, serviço), só aparecem
        # itens da barbearia do usuário.
        if not request.user.is_superuser and hasattr(db_field.related_model, 'barbearia'):
            kwargs['queryset'] = db_field.related_model.objects.filter(barbearia=request.user.barbearia)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Barbearia)
class BarbeariaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'slug', 'telefone', 'agendamento_online', 'criado_em']
    search_fields = ['nome']


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ['username', 'first_name', 'barbearia', 'papel', 'is_active']
    list_filter = ['barbearia', 'papel', 'is_active']
    fieldsets = UserAdmin.fieldsets + (('Barbearia', {'fields': ['barbearia', 'papel']}),)
    add_fieldsets = UserAdmin.add_fieldsets + (('Barbearia', {'fields': ['barbearia', 'papel']}),)


@admin.register(InscricaoPush)
class InscricaoPushAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'navegador', 'criado_em']
    list_filter = ['usuario__barbearia']
    readonly_fields = ['usuario', 'endpoint', 'p256dh', 'auth', 'navegador', 'criado_em']
