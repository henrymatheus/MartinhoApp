from django import forms

from apps.contas.telefones import formato_internacional


class ConfirmarAgendamentoForm(forms.Form):
    nome = forms.CharField(label='Seu nome', max_length=120)
    telefone = forms.CharField(
        label='WhatsApp',
        max_length=20,
        widget=forms.TextInput(attrs={'inputmode': 'tel', 'autocomplete': 'tel', 'placeholder': '(11) 98765-4321'}),
        help_text='Com DDD. A barbearia usa este número para falar com você.',
    )
    # Armadilha para robôs: um campo escondido que pessoas não preenchem.
    # Se vier preenchido, o envio é ignorado.
    site = forms.CharField(required=False, widget=forms.HiddenInput)

    def clean_nome(self):
        return ' '.join(self.cleaned_data['nome'].split())

    def clean_telefone(self):
        telefone = self.cleaned_data['telefone']
        if not formato_internacional(telefone):
            raise forms.ValidationError('Confira o número: informe o DDD e o telefone, por exemplo (11) 98765-4321.')
        return telefone

    def eh_robo(self):
        return bool(self.cleaned_data.get('site'))
