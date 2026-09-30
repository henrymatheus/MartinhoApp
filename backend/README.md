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
   - um projeto **só de desenvolvimento** no Supabase (recomendado; não use o banco de produção);
   - o PostgreSQL instalado na máquina.
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
