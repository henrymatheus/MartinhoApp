from datetime import datetime, timedelta

from django import forms
from django.db import transaction
from django.utils import timezone

from apps.cadastros.models import Barbeiro, Cliente, Servico, encontrar_ou_criar_cliente

from .disponibilidade import ausente_em
from .models import Agendamento, Atendimento, ItemAtendimento


class AgendamentoForm(forms.ModelForm):
    # Data e hora ficam em dois campos na tela; o model tem um só (inicio).
    data = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'))
    hora = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time', 'step': 300}, format='%H:%M'))
    # Só aparece na tela quando o barbeiro está ausente no horário escolhido.
    agendar_mesmo_assim = forms.BooleanField(label='Agendar mesmo assim (encaixe)', required=False)

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

            # A barbearia pode agendar com um barbeiro ausente (um encaixe, por
            # exemplo), mas precisa confirmar de propósito.
            barbeiro, servico = dados.get('barbeiro'), dados.get('servico')
            if barbeiro and servico and not dados.get('agendar_mesmo_assim'):
                fim = self.instance.inicio + timedelta(minutes=servico.duracao_minutos)
                if ausente_em(barbeiro, self.instance.inicio, fim):
                    self.ausencia_detectada = True
                    raise forms.ValidationError(
                        f'{barbeiro} está ausente nesse horário. Escolha outro barbeiro ou horário, '
                        'ou marque "Agendar mesmo assim".'
                    )
        return dados


class AtendimentoAvulsoForm(forms.Form):
    """
    Registra um atendimento de quem chegou sem hora marcada.

    Não cria agendamento: o atendimento já aconteceu (ou está acontecendo),
    então vai direto para a ficha do cliente e para o histórico. O cliente
    é escolhido da lista ou cadastrado ali mesmo, só com nome e WhatsApp.
    """

    cliente = forms.ModelChoiceField(
        label='Cliente cadastrado', queryset=Cliente.objects.none(), required=False, empty_label='Escolha um cliente'
    )
    novo_nome = forms.CharField(label='Nome', max_length=120, required=False)
    novo_telefone = forms.CharField(
        label='WhatsApp',
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'inputmode': 'tel', 'placeholder': '(11) 98765-4321'}),
        help_text='Se o número já estiver cadastrado, o atendimento vai para a ficha existente.',
    )
    barbeiro = forms.ModelChoiceField(queryset=Barbeiro.objects.none(), empty_label=None)
    # Os serviços feitos (corte, barba...): dão o valor do atendimento no
    # histórico. Pode marcar mais de um.
    servicos = forms.ModelMultipleChoiceField(
        label='Serviços',
        queryset=Servico.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        error_messages={'required': 'Marque pelo menos um serviço.'},
    )
    data = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'))
    observacoes = forms.CharField(label='Observações', required=False, widget=forms.Textarea(attrs={'rows': 2}))

    def __init__(self, *args, barbearia, barbeiros, **kwargs):
        """`barbeiros`: com quem o usuário pode registrar (o barbeiro, só consigo mesmo)."""
        super().__init__(*args, **kwargs)
        self.barbearia = barbearia
        self.fields['cliente'].queryset = Cliente.objects.filter(barbearia=barbearia)
        self.fields['barbeiro'].queryset = barbeiros
        self.fields['servicos'].queryset = Servico.objects.filter(barbearia=barbearia, ativo=True)
        self.fields['servicos'].label_from_instance = lambda s: f'{s.nome} · R$ {s.preco}'
        self.initial.setdefault('data', timezone.localdate())
        possiveis = list(barbeiros)
        if len(possiveis) == 1:
            # Só um barbeiro possível: não há o que escolher.
            self.unico_barbeiro = possiveis[0]
            self.initial['barbeiro'] = self.unico_barbeiro.pk
            self.fields['barbeiro'].widget = forms.HiddenInput()

    def clean_data(self):
        data = self.cleaned_data['data']
        if data > timezone.localdate():
            raise forms.ValidationError('O atendimento não pode ser numa data futura. Para isso, use o agendamento.')
        return data

    def clean(self):
        dados = super().clean()
        if not dados.get('cliente') and not dados.get('novo_nome', '').strip():
            raise forms.ValidationError('Escolha um cliente da lista ou preencha o nome do cliente novo.')
        return dados

    @transaction.atomic
    def save(self):
        """
        Grava cliente novo (se for o caso), atendimento e serviços juntos:
        tudo ou nada.

        Cada serviço marcado vira um item do atendimento, com o nome e o
        preço do cadastro copiados naquele momento (ItemAtendimento.save).
        """
        dados = self.cleaned_data
        cliente = dados['cliente']
        if cliente is None:
            nome, telefone = dados['novo_nome'].strip(), dados['novo_telefone'].strip()
            if telefone:
                cliente = encontrar_ou_criar_cliente(self.barbearia, nome, telefone)
            else:
                cliente = Cliente.objects.create(barbearia=self.barbearia, nome=nome)
        atendimento = Atendimento.objects.create(
            barbearia=self.barbearia,
            cliente=cliente,
            barbeiro=dados['barbeiro'],
            data=dados['data'],
            observacoes=dados['observacoes'],
        )
        for servico in dados['servicos']:
            ItemAtendimento.objects.create(atendimento=atendimento, servico=servico)
        return atendimento
