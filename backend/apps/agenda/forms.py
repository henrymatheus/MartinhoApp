from datetime import datetime

from django import forms
from django.utils import timezone

from apps.cadastros.models import Barbeiro, Cliente, Servico

from .models import Agendamento


class AgendamentoForm(forms.ModelForm):
    # Data e hora ficam em dois campos na tela; o model tem um só (inicio).
    data = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'))
    hora = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time', 'step': 300}, format='%H:%M'))

    class Meta:
        model = Agendamento
        fields = ['cliente', 'barbeiro', 'servico', 'observacoes']
        widgets = {'observacoes': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, barbearia, **kwargs):
        super().__init__(*args, **kwargs)
        # A barbearia vem da tela, não do formulário: o usuário não escolhe.
        self.instance.barbearia = barbearia
        # Nas listas só aparecem itens desta barbearia, e só os ativos.
        self.fields['cliente'].queryset = Cliente.objects.filter(barbearia=barbearia)
        self.fields['barbeiro'].queryset = Barbeiro.objects.filter(barbearia=barbearia, ativo=True)
        self.fields['servico'].queryset = Servico.objects.filter(barbearia=barbearia, ativo=True)
        self.fields['servico'].label_from_instance = lambda s: f'{s.nome} · {s.duracao_minutos} min · R$ {s.preco}'
        if self.instance.pk:
            inicio = timezone.localtime(self.instance.inicio)
            self.initial.setdefault('data', inicio.date())
            self.initial.setdefault('hora', inicio.time())

    def clean(self):
        dados = super().clean()
        data, hora = dados.get('data'), dados.get('hora')
        if data and hora:
            # Monta o início no fuso de São Paulo. Isto roda antes da validação
            # do model, que calcula o fim e verifica o conflito de horário.
            self.instance.inicio = timezone.make_aware(datetime.combine(data, hora))
            # Ao remarcar, o fim antigo não vale mais: é recalculado pelo serviço.
            self.instance.fim = None
        return dados
