-- =====================================================================
-- RLS (Row Level Security): o isolamento entre barbearias
-- =====================================================================
--
-- O navegador fala com o banco usando a chave pública (anon key) e o
-- login do usuário. Sem RLS, qualquer usuário logado poderia ler as
-- tabelas inteiras pela API. Com RLS, o Postgres acrescenta a cada
-- consulta a condição da política: "só as linhas da minha barbearia".
--
-- No Django esse filtro era o DaBarbeariaMixin, repetido em cada tela.
-- Aqui ele vale para qualquer caminho de acesso: telas, API, scripts com
-- login de usuário. Esquecer o filtro numa tela nova não vaza dados.
--
-- Quem ignora a RLS: só a chave service_role, usada exclusivamente no
-- servidor (painel do superadmin, envio de push). Ela nunca vai para o
-- navegador.
--
-- Papéis:
--   anon           visitante sem login (página de agendamento). Não lê
--                  nenhuma tabela; só chama as funções públicas da
--                  próxima migration.
--   authenticated  usuário logado (dono ou barbeiro).
-- =====================================================================

-- ---------------------------------------------------------------------
-- Funções de apoio das políticas
-- ---------------------------------------------------------------------
-- security definer: rodam com o dono da função (postgres), não com o
-- usuário. Sem isso, a política de "perfis" consultaria "perfis", que
-- aplicaria a política de novo, num laço infinito.
-- set search_path = '': impede que alguém crie uma tabela "perfis" em
-- outro schema para enganar a função (recomendação do Supabase).

create function privado.minha_barbearia() returns bigint
language sql stable security definer set search_path = '' as $$
  select barbearia_id from public.perfis where id = auth.uid()
$$;

create function privado.meu_papel() returns text
language sql stable security definer set search_path = '' as $$
  select papel from public.perfis where id = auth.uid()
$$;

create function privado.sou_dono() returns boolean
language sql stable security definer set search_path = '' as $$
  select coalesce(
    (select papel = 'dono' and barbearia_id is not null from public.perfis where id = auth.uid()),
    false
  )
$$;

-- O barbeiro ligado ao login (ou nulo).
create function privado.meu_barbeiro() returns bigint
language sql stable security definer set search_path = '' as $$
  select b.id from public.barbeiros b
   where b.usuario_id = auth.uid() and b.barbearia_id = privado.minha_barbearia()
$$;

-- As políticas são avaliadas com as permissões do usuário, então ele
-- precisa poder chamar estas funções. O schema "privado" não é publicado
-- na API, então elas não viram endpoints.
grant usage on schema privado to authenticated;
grant execute on function privado.minha_barbearia(), privado.meu_papel(),
  privado.sou_dono(), privado.meu_barbeiro() to authenticated;

-- ---------------------------------------------------------------------
-- Permissões de base
-- ---------------------------------------------------------------------
-- O Supabase dá acesso às tabelas novas para anon e authenticated por
-- padrão, contando com a RLS. Tiramos tudo do anon, por garantia extra:
-- mesmo que uma política fosse escrita errada, o visitante não lê nada.
revoke all on all tables in schema public from anon;
revoke all on all sequences in schema public from anon;
alter default privileges in schema public revoke all on tables from anon;

grant select, insert, update, delete on all tables in schema public to authenticated;
grant usage on all sequences in schema public to authenticated;

-- (select f()) em vez de f(): o Postgres calcula uma vez por consulta, e
-- não uma vez por linha. Recomendação de desempenho do Supabase.

-- ---------------------------------------------------------------------
-- barbearias: cada um vê a sua; só o dono altera. Criar barbearia é com
-- o superadmin (pelo servidor).
-- ---------------------------------------------------------------------
alter table public.barbearias enable row level security;
create policy "ver a minha barbearia" on public.barbearias for select to authenticated
  using (id = (select privado.minha_barbearia()));
create policy "dono altera a barbearia" on public.barbearias for update to authenticated
  using (id = (select privado.minha_barbearia()) and (select privado.sou_dono()))
  with check (id = (select privado.minha_barbearia()));

-- ---------------------------------------------------------------------
-- perfis: vê o próprio e os colegas da barbearia (para ligar login a
-- barbeiro). Ninguém altera pela API: papel e barbearia são definidos
-- pelo superadmin ou pelo dono, sempre por uma ação do servidor.
-- ---------------------------------------------------------------------
alter table public.perfis enable row level security;
create policy "ver perfis da barbearia" on public.perfis for select to authenticated
  using (id = (select auth.uid()) or barbearia_id = (select privado.minha_barbearia()));

-- ---------------------------------------------------------------------
-- barbeiros e serviços: todos da barbearia veem; só o dono cadastra.
-- ---------------------------------------------------------------------
alter table public.barbeiros enable row level security;
create policy "ver barbeiros" on public.barbeiros for select to authenticated
  using (barbearia_id = (select privado.minha_barbearia()));
create policy "dono cadastra barbeiros" on public.barbeiros for all to authenticated
  using (barbearia_id = (select privado.minha_barbearia()) and (select privado.sou_dono()))
  with check (barbearia_id = (select privado.minha_barbearia()) and (select privado.sou_dono()));

alter table public.servicos enable row level security;
create policy "ver servicos" on public.servicos for select to authenticated
  using (barbearia_id = (select privado.minha_barbearia()));
create policy "dono cadastra servicos" on public.servicos for all to authenticated
  using (barbearia_id = (select privado.minha_barbearia()) and (select privado.sou_dono()))
  with check (barbearia_id = (select privado.minha_barbearia()) and (select privado.sou_dono()));

-- ---------------------------------------------------------------------
-- clientes: toda a equipe vê e cadastra; apagar, só o dono.
-- ---------------------------------------------------------------------
alter table public.clientes enable row level security;
create policy "ver clientes" on public.clientes for select to authenticated
  using (barbearia_id = (select privado.minha_barbearia()));
create policy "cadastrar clientes" on public.clientes for insert to authenticated
  with check (barbearia_id = (select privado.minha_barbearia()));
create policy "editar clientes" on public.clientes for update to authenticated
  using (barbearia_id = (select privado.minha_barbearia()))
  with check (barbearia_id = (select privado.minha_barbearia()));
create policy "dono apaga clientes" on public.clientes for delete to authenticated
  using (barbearia_id = (select privado.minha_barbearia()) and (select privado.sou_dono()));

-- ---------------------------------------------------------------------
-- horários e ausências: todos veem (a agenda mostra a equipe do dia);
-- o dono edita os de todos, o barbeiro só os próprios.
-- Mudança em relação ao Django: lá, um login de barbeiro SEM ficha ligada
-- editava os horários de todos. Aqui ele não edita nenhum.
-- ---------------------------------------------------------------------
alter table public.horarios_trabalho enable row level security;
create policy "ver horarios" on public.horarios_trabalho for select to authenticated
  using (barbearia_id = (select privado.minha_barbearia()));
create policy "editar horarios" on public.horarios_trabalho for all to authenticated
  using (barbearia_id = (select privado.minha_barbearia())
         and ((select privado.sou_dono()) or barbeiro_id = (select privado.meu_barbeiro())))
  with check (barbearia_id = (select privado.minha_barbearia())
              and ((select privado.sou_dono()) or barbeiro_id = (select privado.meu_barbeiro())));

alter table public.ausencias enable row level security;
create policy "ver ausencias" on public.ausencias for select to authenticated
  using (barbearia_id = (select privado.minha_barbearia()));
create policy "editar ausencias" on public.ausencias for all to authenticated
  using (barbearia_id = (select privado.minha_barbearia())
         and ((select privado.sou_dono()) or barbeiro_id = (select privado.meu_barbeiro())))
  with check (barbearia_id = (select privado.minha_barbearia())
              and ((select privado.sou_dono()) or barbeiro_id = (select privado.meu_barbeiro())));

-- ---------------------------------------------------------------------
-- agendamentos: toda a equipe vê, marca e muda o status. Não se apaga
-- agendamento: cancela-se (o histórico de faltas e cancelamentos fica).
-- ---------------------------------------------------------------------
alter table public.agendamentos enable row level security;
create policy "ver agendamentos" on public.agendamentos for select to authenticated
  using (barbearia_id = (select privado.minha_barbearia()));
create policy "marcar agendamentos" on public.agendamentos for insert to authenticated
  with check (barbearia_id = (select privado.minha_barbearia()));
create policy "alterar agendamentos" on public.agendamentos for update to authenticated
  using (barbearia_id = (select privado.minha_barbearia()))
  with check (barbearia_id = (select privado.minha_barbearia()));

-- ---------------------------------------------------------------------
-- atendimentos e itens: toda a equipe vê (ficha do cliente) e registra;
-- corrigir ou apagar, só o dono. A regra "o barbeiro só registra
-- atendimento avulso para si mesmo" está na função registrar_atendimento.
-- ---------------------------------------------------------------------
alter table public.atendimentos enable row level security;
create policy "ver atendimentos" on public.atendimentos for select to authenticated
  using (barbearia_id = (select privado.minha_barbearia()));
create policy "registrar atendimentos" on public.atendimentos for insert to authenticated
  with check (barbearia_id = (select privado.minha_barbearia()));
create policy "dono corrige atendimentos" on public.atendimentos for update to authenticated
  using (barbearia_id = (select privado.minha_barbearia()) and (select privado.sou_dono()))
  with check (barbearia_id = (select privado.minha_barbearia()));
create policy "dono apaga atendimentos" on public.atendimentos for delete to authenticated
  using (barbearia_id = (select privado.minha_barbearia()) and (select privado.sou_dono()));

alter table public.itens_atendimento enable row level security;
create policy "ver itens" on public.itens_atendimento for select to authenticated
  using (barbearia_id = (select privado.minha_barbearia()));
create policy "registrar itens" on public.itens_atendimento for insert to authenticated
  with check (barbearia_id = (select privado.minha_barbearia()));
create policy "dono corrige itens" on public.itens_atendimento for update to authenticated
  using (barbearia_id = (select privado.minha_barbearia()) and (select privado.sou_dono()))
  with check (barbearia_id = (select privado.minha_barbearia()));
create policy "dono apaga itens" on public.itens_atendimento for delete to authenticated
  using (barbearia_id = (select privado.minha_barbearia()) and (select privado.sou_dono()));

-- ---------------------------------------------------------------------
-- inscrições push: cada um só mexe nos próprios aparelhos.
-- ---------------------------------------------------------------------
alter table public.inscricoes_push enable row level security;
create policy "meus aparelhos" on public.inscricoes_push for all to authenticated
  using (usuario_id = (select auth.uid()))
  with check (usuario_id = (select auth.uid()));
