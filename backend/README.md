# Martinho (Django)

## Rodar localmente

Dentro da pasta `backend`:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

- Sistema: http://127.0.0.1:8000/ (login, agenda, clientes)
- Administração: http://127.0.0.1:8000/admin/ (barbearias, usuários, barbeiros, serviços)
- Agendamento do cliente: http://127.0.0.1:8000/agendar/<endereço-da-barbearia>/ (sem login)

## Dados de demonstração

Para ver o sistema funcionando com barbeiros, clientes e uma agenda de hoje:

```powershell
python manage.py dados_demo
```

Entre com usuário `demo` e senha `martinho123`. O comando só roda no SQLite, para não misturar dados falsos com os da barbearia. Para recriar do zero: `python manage.py dados_demo --recriar`.

Não é preciso configurar nada: sem `.env`, o projeto usa SQLite (`db.sqlite3`) e DEBUG ligado. Para conferir se o terminal está usando a venv, rode `python -c "import sys; print(sys.executable)"`: o caminho deve terminar em `backend\.venv\Scripts\python.exe`.

## Produção (Render)

Web Service ligado ao repositório, com:

| Campo | Valor |
|---|---|
| Root Directory | `backend` |
| Build Command | `pip install -r requirements.txt && python manage.py collectstatic --no-input && python manage.py migrate` |
| Start Command | `gunicorn config.wsgi:application` |

Variáveis de ambiente: `DJANGO_SECRET_KEY` e `DATABASE_URL` (Supabase). O endereço `.onrender.com` é liberado automaticamente.

## Testes

```powershell
python manage.py test apps
```

## Organização

| Pasta | O que tem |
|---|---|
| `apps/contas` | `Barbearia`, `Usuario`, a base `PertenceABarbearia` e o `DaBarbeariaMixin` das telas |
| `apps/cadastros` | `Barbeiro`, `Servico`, `Cliente`, `HorarioTrabalho`, `Bloqueio` e as telas de clientes e horários |
| `apps/agenda` | `Agendamento`, `Atendimento`, `ItemAtendimento`, a agenda do dia, o cálculo de horários livres (`disponibilidade.py`) e o comando `dados_demo` |
| `apps/publico` | Página de agendamento do cliente (sem login) e os arquivos do PWA |
| `templates/` | `base.html` (topo e menu), tela de login e trechos reaproveitados |
| `static/css/` | `tokens.css` (cores da marca, gerado de `docs/marca/tokens.json`) e `martinho.css` |
