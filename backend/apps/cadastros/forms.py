from django import forms
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction

from .logos import validar_logo
from .models import Bloqueio, Cliente, HorarioTrabalho, Parceiro, Servico


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['nome', 'telefone', 'email', 'data_nascimento', 'endereco', 'observacoes']
        widgets = {
            'telefone': forms.TextInput(attrs={'inputmode': 'tel', 'placeholder': '(11) 98765-4321'}),
            'email': forms.EmailInput(attrs={'inputmode': 'email'}),
            'data_nascimento': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'observacoes': forms.Textarea(attrs={'rows': 3}),
        }
        help_texts = {
            'telefone': 'Com DDD. Usado para os lembretes no WhatsApp.',
            'data_nascimento': 'Para o e-mail e o aviso de aniversário.',
        }

    def __init__(self, *args, barbearia, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.barbearia = barbearia


class SemanaForm(forms.Form):
    """
    Os turnos da semana de um barbeiro numa tela só.

    Para cada dia: "atende?" e até dois turnos (manhã e tarde). O intervalo
    entre os turnos é o almoço. Ao salvar, os turnos antigos são trocados
    pelos novos.
    """

    TURNOS = 2

    def __init__(self, *args, barbeiro, **kwargs):
        super().__init__(*args, **kwargs)
        self.barbeiro = barbeiro
        existentes = {}
        for turno in barbeiro.horarios.all():
            existentes.setdefault(turno.dia_semana, []).append(turno)

        hora = {'widget': forms.TimeInput(attrs={'type': 'time', 'step': 900}, format='%H:%M'), 'required': False}
        for dia, nome in HorarioTrabalho.DiaSemana.choices:
            turnos = existentes.get(dia, [])
            self.fields[f'd{dia}_ativo'] = forms.BooleanField(label=nome, required=False, initial=bool(turnos))
            for n in range(1, self.TURNOS + 1):
                turno = turnos[n - 1] if len(turnos) >= n else None
                self.fields[f'd{dia}_inicio{n}'] = forms.TimeField(label='Início', initial=turno and turno.inicio, **hora)
                self.fields[f'd{dia}_fim{n}'] = forms.TimeField(label='Fim', initial=turno and turno.fim, **hora)

    def dias(self):
        """Para o template: uma linha por dia, com os campos de cada turno."""
        for dia, nome in HorarioTrabalho.DiaSemana.choices:
            yield {
                'nome': nome,
                'ativo': self[f'd{dia}_ativo'],
                'turnos': [(self[f'd{dia}_inicio{n}'], self[f'd{dia}_fim{n}']) for n in range(1, self.TURNOS + 1)],
            }

    def clean(self):
        dados = super().clean()
        self.turnos = []
        for dia, nome in HorarioTrabalho.DiaSemana.choices:
            if not dados.get(f'd{dia}_ativo'):
                continue
            fim_anterior = None
            for n in range(1, self.TURNOS + 1):
                inicio, fim = dados.get(f'd{dia}_inicio{n}'), dados.get(f'd{dia}_fim{n}')
                if n > 1 and not inicio and not fim:
                    continue  # segundo turno é opcional
                if not inicio or not fim:
                    self.add_error(f'd{dia}_inicio{n}', f'{nome}: preencha o início e o fim.')
                elif fim <= inicio:
                    self.add_error(f'd{dia}_fim{n}', f'{nome}: o fim precisa ser depois do início.')
                elif fim_anterior and inicio < fim_anterior:
                    self.add_error(f'd{dia}_inicio{n}', f'{nome}: a tarde precisa começar depois do fim da manhã.')
                else:
                    self.turnos.append(HorarioTrabalho(barbeiro=self.barbeiro, dia_semana=dia, inicio=inicio, fim=fim))
                    fim_anterior = fim
        return dados

    @transaction.atomic
    def save(self):
        self.barbeiro.horarios.all().delete()
        HorarioTrabalho.objects.bulk_create(self.turnos)


class BloqueioForm(forms.ModelForm):
    class Meta:
        model = Bloqueio
        fields = ['data_inicio', 'data_fim', 'hora_inicio', 'hora_fim', 'motivo']
        widgets = {
            'data_inicio': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'data_fim': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'hora_inicio': forms.TimeInput(attrs={'type': 'time', 'step': 900}, format='%H:%M'),
            'hora_fim': forms.TimeInput(attrs={'type': 'time', 'step': 900}, format='%H:%M'),
            'motivo': forms.TextInput(attrs={'placeholder': 'Folga, férias, consulta…'}),
        }
        help_texts = {'hora_inicio': 'Deixe em branco para o dia inteiro.'}

    def __init__(self, *args, barbeiro, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.barbeiro = barbeiro


class ServicoForm(forms.ModelForm):
    class Meta:
        model = Servico
        fields = ['nome', 'preco', 'duracao_minutos', 'ativo']
        # Preço no formato brasileiro: aceita "45,50" (e também "45.50").
        localized_fields = ['preco']
        widgets = {
            'preco': forms.TextInput(attrs={'inputmode': 'decimal', 'placeholder': '45,00'}),
            'duracao_minutos': forms.NumberInput(attrs={'min': 5, 'step': 5}),
        }
        help_texts = {
            'preco': 'O novo preço vale para os próximos atendimentos. O histórico guarda o preço do dia.',
            'duracao_minutos': 'Define quanto tempo o horário ocupa na agenda.',
            'ativo': 'Desmarque para tirar o serviço da agenda e da página de agendamento. O histórico continua.',
        }

    def __init__(self, *args, barbearia, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.barbearia = barbearia

    def clean_nome(self):
        # O banco já impede dois serviços com o mesmo nome na barbearia; aqui
        # a mensagem sai amigável (e sem diferenciar maiúsculas) em vez de erro.
        nome = self.cleaned_data['nome'].strip()
        repetido = Servico.objects.filter(barbearia=self.instance.barbearia, nome__iexact=nome).exclude(pk=self.instance.pk)
        if repetido.exists():
            raise forms.ValidationError('Já existe um serviço com esse nome.')
        return nome


class ParceiroForm(forms.ModelForm):
    class Meta:
        model = Parceiro
        fields = ['nome', 'logo', 'link', 'ordem']
        widgets = {
            # FileInput simples: sem o "Atualmente: <caminho>" do widget padrão.
            'logo': forms.FileInput(attrs={'accept': '.png,.jpg,.jpeg,.svg,image/png,image/jpeg,image/svg+xml'}),
            'link': forms.URLInput(attrs={'placeholder': 'https://'}),
        }
        help_texts = {'logo': 'PNG, JPG ou SVG, até 2 MB. Fundo transparente fica melhor.'}

    def __init__(self, *args, barbearia, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.barbearia = barbearia
        self.logo_anterior = self.instance.logo.name if self.instance.pk else ''
        if self.instance.pk:
            self.fields['logo'].required = False
            self.fields['logo'].help_text = 'Envie só se quiser trocar a logo. ' + self.fields['logo'].help_text

    def clean_logo(self):
        arquivo = self.cleaned_data.get('logo')
        # Na edição sem arquivo novo, chega a logo atual (já validada).
        if isinstance(arquivo, UploadedFile):
            extensao = validar_logo(arquivo)
            arquivo.name = f'logo{extensao}'  # o caminho final é sorteado em caminho_da_logo
        return arquivo

    def save(self, commit=True):
        parceiro = super().save(commit)
        # Trocou a logo: apaga o arquivo antigo do armazenamento.
        if commit and self.logo_anterior and parceiro.logo.name != self.logo_anterior:
            default_storage.delete(self.logo_anterior)
        return parceiro
