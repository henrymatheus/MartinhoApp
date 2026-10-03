# Sistema Barbearia AD JOM

Aplicação desktop em Python para gerenciamento de clientes, atendimentos, produtos e agendamentos de uma barbearia.

## Funcionalidades
- Cadastro, edição e busca de clientes.
- Registro de atendimentos com serviços e produtos.
- Geração de histórico de atendimentos (exporta para Excel).
- Visualização e busca de agendamentos.
- Interface GUI com ttkbootstrap e tkcalendar.

## Tecnologias / Dependências
- Python 3.8+
- tkinter (GUI)
- ttkbootstrap
- tkcalendar
- pandas (exportar Excel)
- sqlite3 (banco local)
- phonenumbers
- email_validator
- openpyxl (para salvar .xlsx)

Instale dependências:
```bash

pip install ttkbootstrap tkcalendar pandas phonenumbers email-validator openpyxl

Estrutura principal
main.py — interface e lógica principal (classe barbearia)
agendamento.py — função main() usada para carregar agendamentos (agendamento.py)
EnvioEmail.py — utilitários de envio de e-mails (EnvioEmail.py)
barbearia.db — banco SQLite (criar conforme scripts do projeto)
assets: icons/, image/
Como executar
Garanta que as dependências estejam instaladas.
Tenha o arquivo do banco (barbearia.db) configurado com as tabelas: clientes, servicos, produtos, atendimentos.
Execute:
python [main.py](http://_vscodecontentref_/16)

Observações
Exportação de histórico usa pandas (to_excel) — verifique openpyxl.
A listagem de agendamentos utiliza a função main() em agendamento.py (veja barbearia.lista_de_agendamentos).
Insira os arquivos de credenciais (ex.: client_secret.json, token.json) com segurança — veja senhas.txt apenas para referência local.
Contribuição
Abra issues e pull requests. Mantenha código limpo e com testes.

