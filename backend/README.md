# Martinho — back-end (Django)

## Rodar localmente

1. Crie a venv e instale as dependências:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate        # Windows
   pip install -r requirements.txt
   ```
2. Copie `.env.example` para `.env` e preencha `DJANGO_SECRET_KEY` e `DATABASE_URL`.
3. Tenha um PostgreSQL disponível. É obrigatório: a regra de conflito de horários usa um recurso que só o PostgreSQL tem. Duas opções:
   - o PostgreSQL local em `%LOCALAPPDATA%\Martinho\postgres` (porta 55432). Ligue antes de trabalhar:
     `powershell -ExecutionPolicy Bypass -File scripts\banco-local.ps1 ligar`
     (também aceita `desligar` e `status`). `DATABASE_URL=postgres://martinho@localhost:55432/postgres`;
   - um projeto **só de desenvolvimento** no Supabase (não use o banco de produção).
4. Crie as tabelas e um superusuário:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   python manage.py runserver
   ```
   O admin fica em http://localhost:8000/admin/.

## Testes

```bash
python manage.py test apps
```

## Organização

| App | Models |
|---|---|
| `apps/contas` | `Barbearia`, `Usuario` e a base `PertenceABarbearia` |
| `apps/cadastros` | `Barbeiro`, `Servico`, `Cliente` |
| `apps/agenda` | `Agendamento`, `Atendimento`, `ItemAtendimento` |
