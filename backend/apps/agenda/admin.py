from django.contrib import admin

from apps.contas.admin import DaBarbeariaAdmin

from .models import Agendamento, Atendimento, ItemAtendimento


@admin.register(Agendamento)
class AgendamentoAdmin(DaBarbeariaAdmin):
    list_display = ['inicio', 'fim', 'cliente', 'barbeiro', 'servico', 'status']
    list_filter = ['status', 'barbeiro', 'barbearia']
    date_hierarchy = 'inicio'
    search_fields = ['cliente__nome']
    list_select_related = ['cliente', 'barbeiro', 'servico']


class ItemAtendimentoInline(admin.TabularInline):
    model = ItemAtendimento
    extra = 1

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'servico' and not request.user.is_superuser:
            kwargs['queryset'] = db_field.related_model.objects.filter(barbearia=request.user.barbearia)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Atendimento)
class AtendimentoAdmin(DaBarbeariaAdmin):
    list_display = ['data', 'cliente', 'barbeiro', 'total']
    list_filter = ['barbeiro', 'barbearia']
    date_hierarchy = 'data'
    search_fields = ['cliente__nome']
    list_select_related = ['cliente', 'barbeiro']
    inlines = [ItemAtendimentoInline]
