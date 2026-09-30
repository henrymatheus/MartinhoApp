"""
Cria uma barbearia de demonstração com barbeiros (e seus horários de
trabalho), serviços, clientes, agendamentos de hoje e de amanhã e um
histórico de atendimentos.

Uso:
    python manage.py dados_demo                  # cria o usuário demo / martinho123
    python manage.py dados_demo --usuario henry  # liga um usuário existente à demo
    python manage.py dados_demo --recriar        # apaga a demo e cria de novo

Só roda no SQLite, para nunca misturar dados falsos com os da barbearia real.
"""

from datetime import datetime, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from apps.agenda.models import Agendamento, Atendimento, ItemAtendimento
from apps.cadastros.models import Barbeiro, Bloqueio, Cliente, HorarioTrabalho, Servico
from apps.contas.models import Barbearia, Usuario

NOME_DEMO = 'Barbearia Demo'
SENHA_DEMO = 'martinho123'


class Command(BaseCommand):
    help = 'Cria dados de demonstração (somente no SQLite).'

    def add_arguments(self, parser):
        parser.add_argument('--usuario', help='Usuário existente a ser ligado à barbearia demo.')
        parser.add_argument('--recriar', action='store_true', help='Apaga a barbearia demo e cria de novo.')

    def handle(self, *args, usuario=None, recriar=False, **opcoes):
        if connection.vendor != 'sqlite':
            raise CommandError(
                'Este comando só roda no SQLite, para não misturar dados falsos com os reais. '
                'Comente a linha DATABASE_URL no .env (coloque # no início) e rode de novo.'
            )

        existente = Barbearia.objects.filter(nome=NOME_DEMO).first()
        if existente and not recriar:
            raise CommandError(f'A "{NOME_DEMO}" já existe. Use --recriar para apagar e criar de novo.')

        with transaction.atomic():
            if existente:
                self.apagar(existente)
            barbearia = Barbearia.objects.create(
                nome=NOME_DEMO, telefone='(11) 93456-7890', endereco='Rua Augusta, 1200 · São Paulo'
            )
            login = self.preparar_usuario(barbearia, usuario)
            self.popular(barbearia)

        self.stdout.write(self.style.SUCCESS(f'Pronto: "{NOME_DEMO}" criada.'))
        self.stdout.write(login)
        self.stdout.write('Rode "python manage.py runserver" e abra http://127.0.0.1:8000/')
        self.stdout.write(f'Página de agendamento do cliente: http://127.0.0.1:8000/agendar/{barbearia.slug}/')

    def apagar(self, barbearia):
        # A ordem importa: o banco protege (PROTECT) clientes, barbeiros e
        # serviços que ainda têm agendamentos.
        Atendimento.objects.filter(barbearia=barbearia).delete()
        Agendamento.objects.filter(barbearia=barbearia).delete()
        Cliente.objects.filter(barbearia=barbearia).delete()
        Barbeiro.objects.filter(barbearia=barbearia).delete()
        Servico.objects.filter(barbearia=barbearia).delete()
        Usuario.objects.filter(barbearia=barbearia, username='demo').delete()
        Usuario.objects.filter(barbearia=barbearia).update(barbearia=None)
        barbearia.delete()

    def preparar_usuario(self, barbearia, username):
        if username:
            try:
                usuario = Usuario.objects.get(username=username)
            except Usuario.DoesNotExist:
                raise CommandError(f'Usuário "{username}" não existe. Crie com "python manage.py createsuperuser".')
            usuario.barbearia = barbearia
            usuario.save(update_fields=['barbearia'])
            return f'Entre com o seu usuário "{username}".'
        usuario = Usuario.objects.create_superuser('demo', password=SENHA_DEMO, first_name='Martinho')
        usuario.barbearia = barbearia
        usuario.save(update_fields=['barbearia'])
        return f'Entre com usuário "demo" e senha "{SENHA_DEMO}".'

    def popular(self, barbearia):
        ricardo = Barbeiro.objects.create(barbearia=barbearia, nome='Ricardo', telefone='(11) 98888-1111')
        paulo = Barbeiro.objects.create(barbearia=barbearia, nome='Paulo', telefone='(11) 98888-2222')

        # Expediente: Ricardo de segunda a sábado com almoço; Paulo de terça a
        # sábado, só à tarde no sábado. Paulo tem uma folga daqui a 3 dias.
        def turno(barbeiro, dias, inicio, fim):
            for dia in dias:
                HorarioTrabalho.objects.create(barbeiro=barbeiro, dia_semana=dia, inicio=inicio, fim=fim)

        turno(ricardo, range(0, 6), '09:00', '12:00')
        turno(ricardo, range(0, 6), '13:00', '19:30')
        turno(paulo, range(1, 5), '10:00', '20:00')
        turno(paulo, [5], '13:00', '18:00')
        daqui_3 = timezone.localdate() + timedelta(days=3)
        Bloqueio.objects.create(barbeiro=paulo, data_inicio=daqui_3, data_fim=daqui_3, motivo='Folga')

        def servico(nome, preco, minutos):
            return Servico.objects.create(barbearia=barbearia, nome=nome, preco=Decimal(preco), duracao_minutos=minutos)

        corte = servico('Corte de cabelo', '40.00', 30)
        barba = servico('Barba', '30.00', 30)
        combo = servico('Cabelo e barba', '60.00', 60)
        sobrancelha = servico('Sobrancelha', '15.00', 15)

        hoje = timezone.localdate()

        def cliente(nome, telefone, nascimento=None, email=''):
            return Cliente.objects.create(
                barbearia=barbearia, nome=nome, telefone=telefone, data_nascimento=nascimento, email=email
            )

        # João faz aniversário hoje, para mostrar o marcador dourado.
        # (29/02 não existe em 1990; nesse caso fica 28/02.)
        nascimento_joao = hoje.replace(year=1990) if (hoje.month, hoje.day) != (2, 29) else hoje.replace(year=1990, day=28)
        joao = cliente('João Pereira', '(11) 98765-4321', nascimento_joao, 'joao@exemplo.com')
        carlos = cliente('Carlos Mendes', '(11) 97654-3210', datetime(1985, 3, 14).date())
        rafael = cliente('Rafael Souza', '(11) 96543-2109', datetime(1998, 7, 2).date())
        marcos = cliente('Marcos Lima', '(11) 95432-1098')
        pedro = cliente('Pedro Alves', '(11) 94321-0987', datetime(2001, 11, 23).date())
        lucas = cliente('Lucas Ferreira', '(11) 93210-9876')
        gabriel = cliente('Gabriel Rocha', '(11) 92109-8765', datetime(1993, 5, 30).date())

        def as_(dia, hora, minuto=0):
            return timezone.make_aware(datetime.combine(dia, datetime.min.time()).replace(hour=hora, minute=minuto))

        def agendar(cli, barbeiro, serv, dia, hora, minuto=0, **extra):
            return Agendamento.objects.create(
                barbearia=barbearia, cliente=cli, barbeiro=barbeiro, servico=serv, inicio=as_(dia, hora, minuto), **extra
            )

        # Hoje: horários espalhados pelo dia. Os que já passaram ficam concluídos.
        agora = timezone.now()
        hoje_agenda = [
            (carlos, ricardo, corte, 9, 0),
            (rafael, paulo, combo, 9, 30),
            (marcos, ricardo, barba, 10, 0),
            (pedro, paulo, corte, 11, 0),
            (joao, ricardo, combo, 14, 30),
            (lucas, paulo, sobrancelha, 15, 0),
            (gabriel, ricardo, corte, 16, 0),
            (carlos, paulo, barba, 17, 30),
            (rafael, ricardo, corte, 19, 0),
        ]
        for cli, barbeiro, serv, hora, minuto in hoje_agenda:
            ag = agendar(cli, barbeiro, serv, hoje, hora, minuto)
            if ag.fim <= agora:
                ag.concluir()

        # Amanhã.
        amanha = hoje + timedelta(days=1)
        agendar(pedro, ricardo, combo, amanha, 10, 0)
        agendar(joao, paulo, barba, amanha, 11, 0)
        agendar(gabriel, ricardo, corte, amanha, 15, 30)

        # Histórico dos últimos meses.
        for semanas, cli, barbeiro, serv in [
            (2, joao, ricardo, corte),
            (5, joao, paulo, combo),
            (9, joao, ricardo, corte),
            (3, carlos, ricardo, corte),
            (4, rafael, paulo, barba),
            (6, gabriel, ricardo, combo),
        ]:
            dia = hoje - timedelta(weeks=semanas)
            atendimento = Atendimento.objects.create(barbearia=barbearia, cliente=cli, barbeiro=barbeiro, data=dia)
            ItemAtendimento.objects.create(atendimento=atendimento, servico=serv)
