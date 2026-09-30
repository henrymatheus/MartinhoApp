from django.contrib import admin

from apps.contas.admin import DaBarbeariaAdmin

from .models import Barbeiro, Cliente, Servico


@admin.register(Barbeiro)
class BarbeiroAdmin(DaBarbeariaAdmin):
    list_display = ['nome', 'telefone', 'ativo', 'barbearia']
    list_filter = ['ativo', 'barbearia']
    search_fields = ['nome']


@admin.register(Servico)
class ServicoAdmin(DaBarbeariaAdmin):
    list_display = ['nome', 'preco', 'duracao_minutos', 'ativo', 'barbearia']
    list_filter = ['ativo', 'barbearia']
    search_fields = ['nome']


@admin.register(Cliente)
class ClienteAdmin(DaBarbeariaAdmin):
    list_display = ['nome', 'telefone', 'email', 'data_nascimento', 'barbearia']
    list_filter = ['barbearia']
    search_fields = ['nome', 'telefone', 'email']
