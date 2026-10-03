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

## Produção (Vercel)

O Django roda na Vercel como uma Vercel Function: a Vercel encontra o `manage.py`, usa o `config.wsgi`, roda o `collectstatic` sozinha no build e serve o CSS e as imagens pelo CDN dela. O `settings.py` reconhece que está na Vercel pela variável `VERCEL`.

### Criar o projeto

1. Em vercel.com, **Add New > Project** e importe o repositório do GitHub.
2. **Root Directory**: `backend`. **Application Preset**: Django (aparece sozinho).
3. Em **Environment Variables**, cadastre as variáveis da tabela abaixo e clique em **Deploy**.
4. Em **Settings > Functions > Function Region**, escolha a mesma região do Supabase (São Paulo: `gru1`, se o Supabase estiver em `sa-east-1`).

Cada push na branch `main` publica sozinho. O endereço `.vercel.app` (e o de cada deploy) é liberado automaticamente; para um domínio próprio, acrescente-o em `DJANGO_ALLOWED_HOSTS` e `DJANGO_CSRF_TRUSTED_ORIGINS` (este com `https://`).

| Variável | Para quê |
|---|---|
| `DJANGO_SECRET_KEY` | Chave secreta do Django. Use a mesma do Render, para não derrubar os logins abertos; ou gere uma: `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DATABASE_URL` | Banco do Supabase pelo **Transaction pooler** (Supabase > Connect > Transaction pooler, porta **6543**), com `?sslmode=require` no final |
| `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_EMAIL` | Avisos push ao barbeiro. Use as mesmas do Render, para os celulares já inscritos continuarem recebendo |

Os valores atuais estão no painel do Render (Environment). Copie de lá antes de desligá-lo.

Por que o Transaction pooler: na Vercel o Django roda em várias cópias que nascem e morrem conforme o movimento, e cada requisição abre e fecha a própria conexão. O pooler divide poucas conexões reais do Supabase gratuito entre todas essas cópias.

### Migrations

A Vercel não roda `migrate`. Quando um model mudar, rode na sua máquina, apontando para o banco de produção:

```powershell
$env:DATABASE_URL = "<a mesma DATABASE_URL da Vercel>"
python manage.py migrate
Remove-Item Env:DATABASE_URL
```

> **Plano Hobby da Vercel:** os termos permitem só uso não comercial. Para uso comercial, o plano é o Pro.

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
