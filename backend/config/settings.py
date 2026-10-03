"""
Configurações do Django para o Martinho.

Na sua máquina, o projeto roda sem configurar nada: SQLite e DEBUG ligado.
Em produção (Vercel), os valores vêm de variáveis de ambiente cadastradas
no painel da Vercel: DJANGO_SECRET_KEY, DATABASE_URL (Supabase) etc.
Se quiser mudar algo localmente, crie um backend/.env (veja .env.example).
"""

import os
import sys
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')


def env_bool(nome, padrao=False):
    return os.environ.get(nome, str(padrao)).strip().lower() in ('1', 'true', 'yes', 'sim')


def env_list(nome, padrao=''):
    return [item.strip() for item in os.environ.get(nome, padrao).split(',') if item.strip()]


# A Vercel define a variável VERCEL (e o Render, a RENDER) nos seus
# servidores, inclusive durante o build. Com ela, sabemos que estamos em
# produção sem depender de alguém lembrar de desligar o DEBUG.
NA_VERCEL = 'VERCEL' in os.environ
EM_PRODUCAO = NA_VERCEL or 'RENDER' in os.environ

DEBUG = env_bool('DJANGO_DEBUG', not EM_PRODUCAO)

if DEBUG:
    SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'chave-apenas-para-desenvolvimento')
else:
    # Em produção não há valor padrão: se faltar, o servidor não sobe, em vez
    # de subir com uma chave conhecida.
    SECRET_KEY = os.environ['DJANGO_SECRET_KEY']

ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')

# O Render informa o endereço do site (ex.: martinho.onrender.com) nesta
# variável. Assim não é preciso cadastrá-lo à mão.
RENDER_HOST = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_HOST:
    ALLOWED_HOSTS.append(RENDER_HOST)

# A Vercel informa os endereços do deploy nestas variáveis: o domínio de
# produção (martinho-app.vercel.app ou um domínio próprio), o do branch e
# o endereço único de cada deploy (usado nas pré-visualizações).
VERCEL_HOSTS = [
    os.environ[nome]
    for nome in ('VERCEL_PROJECT_PRODUCTION_URL', 'VERCEL_BRANCH_URL', 'VERCEL_URL')
    if os.environ.get(nome)
]
ALLOWED_HOSTS += VERCEL_HOSTS


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'apps.contas',
    'apps.cadastros',
    'apps.agenda',
    'apps.publico',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # O WhiteNoise serve os arquivos estáticos (CSS do admin) direto pelo
    # Django, sem precisar de um servidor web separado no Render.
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # Templates compartilhados (base.html, login). Os de cada app ficam em
        # apps/<app>/templates/<app>/.
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.contas.contexto.push',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Banco de dados:
# - sem DATABASE_URL (sua máquina): SQLite, no arquivo backend/db.sqlite3;
# - com DATABASE_URL (Vercel): PostgreSQL do Supabase.
#
# Na Vercel o Django não é um servidor sempre ligado: ele roda em várias
# cópias que nascem e morrem conforme o movimento. Se cada cópia segurasse
# uma conexão aberta (conn_max_age), as conexões do Supabase gratuito
# acabariam. Por isso lá cada requisição abre e fecha a sua (conn_max_age=0),
# passando pelo pooler do Supabase em modo "transaction" (porta 6543), que
# divide poucas conexões reais entre muitas cópias.
DATABASES = {
    'default': dj_database_url.config(
        env='DATABASE_URL',
        default=f'sqlite:///{BASE_DIR / "db.sqlite3"}',
        conn_max_age=0 if NA_VERCEL else 600,
        conn_health_checks=not NA_VERCEL,
    ),
}
if NA_VERCEL:
    # No modo "transaction" do pooler, a conexão real pode mudar entre uma
    # consulta e outra; cursores do lado do servidor quebrariam com isso.
    DATABASES['default']['DISABLE_SERVER_SIDE_CURSORS'] = True

# Os testes criam e apagam um banco temporário. Eles usam sempre o SQLite,
# para nunca criar esse banco no servidor do Supabase, mesmo com
# DATABASE_URL configurada no .env.
if 'test' in sys.argv:
    DATABASES['default'] = {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db-testes.sqlite3'}


AUTH_USER_MODEL = 'contas.Usuario'

# Para onde o Django manda quem não está logado, e para onde vai depois de
# entrar ou sair.
LOGIN_URL = 'entrar'
LOGIN_REDIRECT_URL = 'agenda:dia'
LOGOUT_REDIRECT_URL = 'entrar'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
# Datas e horas são gravadas em UTC no banco e convertidas para o fuso de
# São Paulo na exibição.
USE_TZ = True


STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
# CSS, logos e scripts do sistema.
STATICFILES_DIRS = [BASE_DIR / 'static']
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    # Sem "Manifest": a API só serve o CSS/JS do admin, então não precisamos
    # de nomes com hash, e assim os testes rodam sem collectstatic.
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
}
if NA_VERCEL:
    # Na Vercel, o collectstatic roda sozinho no build e os arquivos são
    # servidos pelo CDN dela; o armazenamento padrão do Django basta.
    STORAGES['staticfiles'] = {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Notificações push (aviso de novo agendamento no celular do barbeiro).
# Gere as chaves com: python manage.py gerar_chaves_push
# Sem elas, o botão "Ativar avisos" não aparece e nada é enviado.
VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY', '')
VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY', '')
VAPID_EMAIL = os.environ.get('VAPID_EMAIL', 'mailto:contato@martinho.app')


# Segurança em produção (Vercel e Render servem por HTTPS atrás de um proxy).
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = env_bool('DJANGO_SSL_REDIRECT', True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    CSRF_TRUSTED_ORIGINS = env_list('DJANGO_CSRF_TRUSTED_ORIGINS')
    if RENDER_HOST:
        CSRF_TRUSTED_ORIGINS.append(f'https://{RENDER_HOST}')
    # Formulários enviados a partir dos endereços da Vercel (login, agendamento).
    CSRF_TRUSTED_ORIGINS += [f'https://{host}' for host in VERCEL_HOSTS]
