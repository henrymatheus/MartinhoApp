from django import forms
from django.db import transaction

from .models import Bloqueio, Cliente, HorarioTrabalho


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
