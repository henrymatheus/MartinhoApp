# Instruções do projeto

- Antes de iniciar qualquer tarefa, leia [FEATURES.md](FEATURES.md).
- Ao criar, alterar ou remover uma funcionalidade, atualize o FEATURES.md (status, observações e histórico de alterações) na mesma tarefa.
- Explique claramente as decisões do back-end: o dono do projeto revisa todo o código e quer entender o que é feito.
- Segredos sempre em `web/.env.local` (e nas variáveis da Vercel), nunca no Git.
- O app fica em `web/` (Next.js + Supabase). Rode `npm test` lá antes de concluir uma tarefa.
