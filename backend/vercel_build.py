"""
Passo extra do build na Vercel: aplica as migrations no banco de produção.

A Vercel chama este arquivo (vercel.json > buildCommand) depois de instalar
as dependências e antes de publicar a versão nova. Se o migrate falhar, o
build falha e a versão anterior continua no ar: o código novo nunca roda
contra um banco sem as colunas que ele espera.

Só roda no deploy de produção (branch main). As pré-visualizações (outros
branches) pulam o migrate: senão, um branch em teste alteraria o banco de
produção antes de ser aprovado.

O collectstatic não está aqui porque a Vercel já o roda sozinha quando
existe STATIC_ROOT.
"""

import os
import sys

if os.environ.get('VERCEL_ENV') != 'production':
    print(f"vercel_build: ambiente '{os.environ.get('VERCEL_ENV')}', migrate pulado.")
    sys.exit(0)

# Sem DATABASE_URL o settings.py cai no SQLite: o migrate "daria certo" num
# banco descartável e o erro só apareceria no site. Melhor parar o build.
if not os.environ.get('DATABASE_URL'):
    sys.exit('vercel_build: DATABASE_URL não está disponível no build. Confira as variáveis do projeto na Vercel.')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django  # noqa: E402
from django.core.management import call_command  # noqa: E402

django.setup()
call_command('migrate', interactive=False)
