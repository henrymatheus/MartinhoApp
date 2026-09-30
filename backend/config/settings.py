"""
Configurações do Django para o Martinho.

Tudo que muda entre ambientes (local, Render) ou é segredo vem de variáveis
de ambiente. Em desenvolvimento, elas são lidas do arquivo backend/.env
(veja .env.example). Em produção, são configuradas no painel do Render.
"""

import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')


def env_bool(nome, padrao=False):
    return os.environ.get(nome, str(padrao)).strip().lower() in ('1', 'true', 'yes', 'sim')


def env_list(nome, padrao=''):
    return [item.strip() for item in os.environ.get(nome, padrao).split(',') if item.strip()]


# Sem valor padrão de propósito: se faltar, o servidor não sobe, em vez de
# subir com uma chave conhecida.
SECRET_KEY = os.environ['DJANGO_SECRET_KEY']

DEBUG = env_bool('DJANGO_DEBUG', False)

ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Necessário para a ExclusionConstraint que impede horários sobrepostos.
    'django.contrib.postgres',
    'apps.contas',
    'apps.cadastros',
    'apps.agenda',
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
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Banco de dados: sempre PostgreSQL, informado por DATABASE_URL.
# Não há SQLite de reserva porque a regra de conflito de horários usa um
# recurso que só o PostgreSQL tem.
# conn_max_age reaproveita a conexão entre requisições, o que economiza
# tempo com o Supabase, que fica em outro servidor.
DATABASES = {
    'default': dj_database_url.config(
        env='DATABASE_URL',
        conn_max_age=600,
        conn_health_checks=True,
    ),
}


AUTH_USER_MODEL = 'contas.Usuario'

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
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    # Sem "Manifest": a API só serve o CSS/JS do admin, então não precisamos
    # de nomes com hash, e assim os testes rodam sem collectstatic.
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Segurança em produção (Render serve por HTTPS atrás de um proxy).
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = env_bool('DJANGO_SSL_REDIRECT', True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    CSRF_TRUSTED_ORIGINS = env_list('DJANGO_CSRF_TRUSTED_ORIGINS')
