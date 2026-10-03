-- =====================================================================
-- Regras da agenda em funções do banco
-- =====================================================================
--
-- Por que no banco e não no TypeScript:
--
-- 1. A página de agendamento é pública. O visitante não tem acesso a
--    nenhuma tabela (RLS + revoke da migration anterior); ele só pode
--    chamar as funções publico_* abaixo, que devolvem apenas o necessário
--    (nunca nome ou telefone de outros clientes).
-- 2. "Mostrar os horários livres" e "conferir se o horário escolhido ainda
--    está livre" usam a MESMA função. No Django eram horarios_livres() e
--    esta_livre(); aqui não há como as duas divergirem.
-- 3. Operações de várias etapas (achar ou criar o cliente + agendar,
--    concluir + registrar no histórico) rodam numa transação só: ou tudo
--    é gravado, ou nada.
--
-- security definer  = roda com as permissões do dono da função, ignorando
--                     a RLS. Usado só nas funções públicas, que conferem a
--                     barbearia pelo endereço (slug) antes de tudo.
-- security invoker  = (padrão) roda com as permissões de quem chamou; a RLS
--                     vale normalmente. Usado nas funções do sistema interno.
-- =====================================================================

-- Mesmas constantes da versão Django (disponibilidade.py)
create function privado.intervalo() returns interval language sql immutable as $$ select interval '15 minutes' $$;
create function privado.antecedencia_minima() returns interval language sql immutable as $$ select interval '60 minutes' $$;
create function privado.dias_a_frente() returns int language sql immutable as $$ select 30 $$;
-- Horários futuros que um mesmo telefone pode ter pela página pública.
create function privado.maximo_por_telefone() returns int language sql immutable as $$ select 3 $$;

-- "Dia + hora" no fuso de São Paulo -> instante.
create function privado.instante(p_dia date, p_hora time) returns timestamptz
language sql immutable as $$ select (p_dia + p_hora) at time zone privado.fuso() $$;

-- Instante -> dia no fuso de São Paulo (um horário às 23:30 fica no dia
-- certo, mesmo gravado em UTC).
create function privado.dia_local(p_instante timestamptz) returns date
language sql immutable as $$ select (p_instante at time zone privado.fuso())::date $$;

create function privado.hoje() returns date
language sql stable as $$ select privado.dia_local(now()) $$;

-- 0 = segunda ... 6 = domingo (isodow do Postgres vai de 1 a 7).
create function privado.dia_semana(p_dia date) returns smallint
language sql immutable as $$ select (extract(isodow from p_dia)::int - 1)::smallint $$;

-- ---------------------------------------------------------------------
-- Disponibilidade
-- ---------------------------------------------------------------------

-- Trechos em que o barbeiro está ausente naquele dia. Dia inteiro = da
-- meia-noite à meia-noite seguinte.
create function privado.ausencias_no_dia(p_barbeiro bigint, p_dia date)
returns table (inicio timestamptz, fim timestamptz)
language sql stable as $$
  select
    case when a.hora_inicio is null then privado.instante(p_dia, '00:00') else privado.instante(p_dia, a.hora_inicio) end,
    case when a.hora_inicio is null then privado.instante(p_dia + 1, '00:00') else privado.instante(p_dia, a.hora_fim) end
  from public.ausencias a
  where a.barbeiro_id = p_barbeiro and p_dia between a.data_inicio and a.data_fim
$$;

-- Um horário está livre quando:
-- 1. cabe inteiro num turno do barbeiro naquele dia (um corte de 30 min às
--    11:45 não cabe num turno que termina às 12:00);
-- 2. o barbeiro não está ausente nesse trecho;
-- 3. não se sobrepõe a nenhum agendamento (cancelados não contam);
-- 4. começa pelo menos 1 hora depois de agora.
-- Horários oferecidos a cada 15 min desde o início do turno.
create function privado.horarios_livres(p_barbeiro bigint, p_duracao int, p_dia date, p_agora timestamptz)
returns setof timestamptz
language sql stable as $$
  with candidatos as (
    select gs as inicio
    from public.horarios_trabalho h,
         generate_series(
           privado.instante(p_dia, h.inicio),
           privado.instante(p_dia, h.fim) - make_interval(mins => p_duracao),
           privado.intervalo()
         ) as gs
    where h.barbeiro_id = p_barbeiro and h.dia_semana = privado.dia_semana(p_dia)
  ),
  ocupados as (
    select inicio, fim from privado.ausencias_no_dia(p_barbeiro, p_dia)
    union all
    select ag.inicio, ag.fim from public.agendamentos ag
     where ag.barbeiro_id = p_barbeiro and ag.status <> 'cancelado'
       and ag.inicio < privado.instante(p_dia + 1, '00:00')
       and ag.fim > privado.instante(p_dia, '00:00')
  )
  select c.inicio from candidatos c
  where c.inicio >= p_agora + privado.antecedencia_minima()
    -- Sobreposição: um começa antes de o outro terminar, e vice-versa.
    and not exists (
      select 1 from ocupados o
       where c.inicio < o.fim and c.inicio + make_interval(mins => p_duracao) > o.inicio
    )
  order by c.inicio
$$;

-- Os próximos 30 dias em que o barbeiro tem turno e não está ausente o dia
-- inteiro (ausência de parte do dia não tira o dia).
create function privado.dias_de_atendimento(p_barbeiro bigint, p_hoje date)
returns setof date
language sql stable as $$
  select d::date
  from generate_series(p_hoje, p_hoje + privado.dias_a_frente() - 1, interval '1 day') as d
  where exists (select 1 from public.horarios_trabalho h
                 where h.barbeiro_id = p_barbeiro and h.dia_semana = privado.dia_semana(d::date))
    and not exists (select 1 from public.ausencias a
                     where a.barbeiro_id = p_barbeiro and a.hora_inicio is null
                       and d::date between a.data_inicio and a.data_fim)
  order by 1
$$;

-- Dias (dos próximos 30) em que ainda há horário livre para o serviço.
create function privado.dias_com_horario(p_barbeiro bigint, p_duracao int, p_agora timestamptz)
returns setof date
language sql stable as $$
  select d from privado.dias_de_atendimento(p_barbeiro, privado.dia_local(p_agora)) as d
  where exists (select 1 from privado.horarios_livres(p_barbeiro, p_duracao, d, p_agora))
  order by 1
$$;

create function privado.proximo_horario(p_barbeiro bigint, p_duracao int, p_agora timestamptz)
returns timestamptz
language sql stable as $$
  select min(h)
  from privado.dias_de_atendimento(p_barbeiro, privado.dia_local(p_agora)) as d,
       lateral privado.horarios_livres(p_barbeiro, p_duracao, d, p_agora) as h
$$;

-- Quem já é cliente é reconhecido pelo telefone, e o agendamento vai para
-- a ficha existente, com o histórico. Telefone novo cria cliente novo.
-- security invoker: chamada pelo sistema interno, respeita a RLS; chamada
-- por dentro de uma função pública (definer), roda com as permissões dela.
create function privado.encontrar_ou_criar_cliente(p_barbearia bigint, p_nome text, p_telefone text)
returns bigint
language plpgsql as $$
declare
  v_id bigint;
  v_tel text := public.formato_internacional(p_telefone);
begin
  if v_tel <> '' then
    -- Trava por barbearia + telefone até o fim da transação: dois pedidos
    -- simultâneos do mesmo número novo não criam dois clientes.
    perform pg_advisory_xact_lock(hashtextextended('cliente:' || p_barbearia || ':' || v_tel, 0));
    select id into v_id from public.clientes
     where barbearia_id = p_barbearia and telefone_whatsapp = v_tel
     order by id limit 1;
    if v_id is not null then
      return v_id;
    end if;
  end if;
  insert into public.clientes (barbearia_id, nome, telefone)
  values (p_barbearia, p_nome, coalesce(p_telefone, ''))
  returning id into v_id;
  return v_id;
end $$;

-- ---------------------------------------------------------------------
-- Página pública de agendamento (visitante sem login)
-- ---------------------------------------------------------------------

-- Tudo o que a página precisa, conforme o que o cliente já escolheu.
-- Fluxo: barbeiro (com situação e próximo horário) -> serviço -> dias e
-- horários livres daquele barbeiro -> dados. Escolha inválida é ignorada
-- e o cliente volta ao passo correspondente. Devolve null se a barbearia
-- não existe ou está com o agendamento online desligado.
create function public.agenda_publica(
  p_slug text, p_barbeiro bigint default null, p_servico bigint default null, p_dia date default null
) returns jsonb
language plpgsql stable security definer set search_path = '' as $$
declare
  v_agora timestamptz := now();
  v_hoje date := privado.dia_local(now());
  b public.barbearias;
  v_servicos jsonb;
  v_menor int;
  v_barbeiro record;
  v_servico public.servicos;
  v_dias date[];
  v_dia date;
  v_resultado jsonb;
begin
  select * into b from public.barbearias where slug = p_slug and agendamento_online;
  if not found then
    return null;
  end if;

  select coalesce(jsonb_agg(jsonb_build_object(
           'id', s.id, 'nome', s.nome, 'preco', s.preco, 'duracao_minutos', s.duracao_minutos
         ) order by s.nome), '[]'), min(s.duracao_minutos)
    into v_servicos, v_menor
    from public.servicos s where s.barbearia_id = b.id and s.ativo;

  v_resultado := jsonb_build_object(
    'barbearia', jsonb_build_object('nome', b.nome, 'slug', b.slug, 'telefone', b.telefone,
                                    'endereco', b.endereco, 'whatsapp', public.formato_internacional(b.telefone)),
    'servicos', v_servicos
  );

  -- Só barbeiros ativos com algum horário cadastrado aparecem.
  select br.id, br.nome into v_barbeiro
    from public.barbeiros br
   where br.id = p_barbeiro and br.barbearia_id = b.id and br.ativo
     and exists (select 1 from public.horarios_trabalho h where h.barbeiro_id = br.id);

  if v_barbeiro.id is null then
    -- Passo 1: os cartões dos barbeiros. O serviço ainda não foi escolhido,
    -- então o "próximo horário" usa o serviço mais curto. Quem tem horário
    -- vem primeiro, do mais cedo para o mais tarde.
    return v_resultado || jsonb_build_object('cartoes', coalesce((
      select jsonb_agg(c order by (c->>'proximo') is null, c->>'proximo', c->>'nome')
      from (
        select jsonb_build_object(
          'id', x.id, 'nome', x.nome, 'proximo', x.proximo,
          'hoje', x.proximo is not null and privado.dia_local(x.proximo) = v_hoje,
          'situacao', case
            when x.ausente then 'Ausente hoje'
            when x.trabalha_hoje and (x.proximo is null or privado.dia_local(x.proximo) <> v_hoje) then 'Sem horários livres hoje'
            when x.trabalha_hoje then 'Atendendo hoje'
            else 'Não atende hoje'
          end
        ) as c
        from (
          select br.id, br.nome,
                 case when v_menor is null then null else privado.proximo_horario(br.id, v_menor, v_agora) end as proximo,
                 exists (select 1 from public.ausencias a where a.barbeiro_id = br.id and a.hora_inicio is null
                          and v_hoje between a.data_inicio and a.data_fim) as ausente,
                 exists (select 1 from public.horarios_trabalho h where h.barbeiro_id = br.id
                          and h.dia_semana = privado.dia_semana(v_hoje)) as trabalha_hoje
          from public.barbeiros br
          where br.barbearia_id = b.id and br.ativo
            and exists (select 1 from public.horarios_trabalho h where h.barbeiro_id = br.id)
        ) as x
      ) as cartoes
    ), '[]'));
  end if;

  v_resultado := v_resultado || jsonb_build_object('barbeiro', jsonb_build_object('id', v_barbeiro.id, 'nome', v_barbeiro.nome));

  select * into v_servico from public.servicos where id = p_servico and barbearia_id = b.id and ativo;
  if not found then
    return v_resultado;
  end if;

  select coalesce(array_agg(d order by d), '{}') into v_dias
    from privado.dias_com_horario(v_barbeiro.id, v_servico.duracao_minutos, v_agora) as d;
  -- Sem dia escolhido (ou com um dia que não tem mais horário), abre no
  -- primeiro dia com horário livre.
  v_dia := case when p_dia = any (v_dias) then p_dia else v_dias[1] end;

  return v_resultado || jsonb_build_object(
    'servico', jsonb_build_object('id', v_servico.id, 'nome', v_servico.nome, 'preco', v_servico.preco,
                                  'duracao_minutos', v_servico.duracao_minutos),
    'dias', to_jsonb(v_dias),
    'dia', v_dia,
    'horarios', coalesce((select jsonb_agg(h order by h)
                            from privado.horarios_livres(v_barbeiro.id, v_servico.duracao_minutos, v_dia, v_agora) as h
                           where v_dia is not null), '[]')
  );
end $$;

-- Confirma o agendamento feito pelo cliente. Devolve {ok, id, codigo}
-- ou {erro: '<motivo>'}; a página traduz o motivo numa mensagem.
create function public.agendar_online(
  p_slug text, p_barbeiro bigint, p_servico bigint, p_inicio timestamptz, p_nome text, p_telefone text
) returns jsonb
language plpgsql volatile security definer set search_path = '' as $$
declare
  b public.barbearias;
  v_servico public.servicos;
  v_nome text := regexp_replace(trim(coalesce(p_nome, '')), '\s+', ' ', 'g');
  v_tel text := public.formato_internacional(p_telefone);
  v_cliente bigint;
  v_ag public.agendamentos;
begin
  select * into b from public.barbearias where slug = p_slug and agendamento_online;
  if not found then
    return jsonb_build_object('erro', 'pagina');
  end if;
  if v_nome = '' or length(v_nome) > 120 then
    return jsonb_build_object('erro', 'nome');
  end if;
  if v_tel = '' or length(p_telefone) > 20 then
    return jsonb_build_object('erro', 'telefone');
  end if;

  select * into v_servico from public.servicos where id = p_servico and barbearia_id = b.id and ativo;
  if not found or not exists (
    select 1 from public.barbeiros br where br.id = p_barbeiro and br.barbearia_id = b.id and br.ativo
  ) then
    return jsonb_build_object('erro', 'ocupado');
  end if;

  -- Uma pessoa não pode ocupar a agenda inteira: no máximo 3 horários
  -- futuros por telefone. A trava evita que vários envios simultâneos
  -- do mesmo número passem juntos pelo limite.
  perform pg_advisory_xact_lock(hashtextextended('cliente:' || b.id || ':' || v_tel, 0));
  if (select count(*) from public.agendamentos ag
        join public.clientes c on c.id = ag.cliente_id
       where ag.barbearia_id = b.id and ag.status = 'agendado' and ag.inicio >= now()
         and c.telefone_whatsapp = v_tel) >= privado.maximo_por_telefone() then
    return jsonb_build_object('erro', 'limite', 'maximo', privado.maximo_por_telefone());
  end if;

  -- Confere de novo: entre abrir a página e confirmar, outra pessoa pode
  -- ter pego o horário (ou ele ficou perto demais de agora).
  if not exists (
    select 1 from privado.horarios_livres(p_barbeiro, v_servico.duracao_minutos, privado.dia_local(p_inicio), now()) as h
     where h = p_inicio
  ) then
    return jsonb_build_object('erro', 'ocupado');
  end if;

  begin
    v_cliente := privado.encontrar_ou_criar_cliente(b.id, v_nome, p_telefone);
    insert into public.agendamentos (barbearia_id, cliente_id, barbeiro_id, servico_id, inicio, observacoes)
    values (b.id, v_cliente, p_barbeiro, p_servico, p_inicio, 'Agendado pelo cliente na página online.')
    returning * into v_ag;
  exception when exclusion_violation then
    -- Dois clientes confirmaram o mesmo horário no mesmo instante e o
    -- outro chegou primeiro. O bloco desfaz também o cliente criado.
    return jsonb_build_object('erro', 'ocupado');
  end;

  return jsonb_build_object('ok', true, 'id', v_ag.id, 'codigo', v_ag.codigo_publico);
end $$;

-- Página de confirmação. O endereço leva o código aleatório do
-- agendamento, e não o número; vale por 60 dias, como no Django.
create function public.confirmacao_publica(p_slug text, p_codigo uuid) returns jsonb
language sql stable security definer set search_path = '' as $$
  select jsonb_build_object(
    'barbearia', jsonb_build_object('nome', b.nome, 'slug', b.slug, 'telefone', b.telefone,
                                    'endereco', b.endereco, 'whatsapp', public.formato_internacional(b.telefone)),
    'inicio', ag.inicio, 'status', ag.status,
    'servico', s.nome, 'barbeiro', br.nome, 'cliente', c.nome
  )
  from public.agendamentos ag
  join public.barbearias b on b.id = ag.barbearia_id
  join public.servicos s on s.id = ag.servico_id
  join public.barbeiros br on br.id = ag.barbeiro_id
  join public.clientes c on c.id = ag.cliente_id
  where b.slug = p_slug and ag.codigo_publico = p_codigo
    and ag.criado_em > now() - interval '60 days'
$$;

-- Nome da barbearia para o manifesto do PWA (app instalado).
create function public.barbearia_publica(p_slug text) returns jsonb
language sql stable security definer set search_path = '' as $$
  select jsonb_build_object('nome', nome, 'slug', slug)
  from public.barbearias where slug = p_slug and agendamento_online
$$;

-- ---------------------------------------------------------------------
-- Sistema interno (usuário logado; a RLS vale normalmente)
-- ---------------------------------------------------------------------

-- Marca como concluído e registra o atendimento no histórico do cliente,
-- com o serviço e o preço atuais. Tudo ou nada.
create function public.concluir_agendamento(p_agendamento bigint) returns bigint
language plpgsql security invoker set search_path = '' as $$
declare
  ag public.agendamentos;
  v_atendimento bigint;
begin
  update public.agendamentos set status = 'concluido'
   where id = p_agendamento and status = 'agendado'
  returning * into ag;
  if not found then
    raise exception 'Este agendamento não está mais como agendado.' using errcode = 'P0001';
  end if;

  insert into public.atendimentos (barbearia_id, cliente_id, barbeiro_id, agendamento_id, data, observacoes)
  values (ag.barbearia_id, ag.cliente_id, ag.barbeiro_id, ag.id, privado.dia_local(ag.inicio), ag.observacoes)
  on conflict (agendamento_id) do nothing
  returning id into v_atendimento;

  if v_atendimento is not null then
    insert into public.itens_atendimento (barbearia_id, atendimento_id, servico_id)
    values (ag.barbearia_id, v_atendimento, ag.servico_id);
  end if;
  return v_atendimento;
end $$;

-- Atendimento de quem chegou sem hora marcada: vai direto para o histórico
-- e o balanço, sem itens (sem valor) por decisão do dono.
create function public.registrar_atendimento(
  p_cliente bigint, p_novo_nome text, p_novo_telefone text, p_barbeiro bigint, p_data date, p_observacoes text
) returns jsonb
language plpgsql security invoker set search_path = '' as $$
declare
  v_barbearia bigint := privado.minha_barbearia();
  v_cliente bigint := p_cliente;
  v_nome text := regexp_replace(trim(coalesce(p_novo_nome, '')), '\s+', ' ', 'g');
  v_id bigint;
begin
  if v_barbearia is null then
    raise exception 'Usuário sem barbearia.' using errcode = '42501';
  end if;
  -- O barbeiro registra só para si mesmo; o dono, para qualquer barbeiro ativo.
  if privado.meu_papel() = 'barbeiro' then
    if privado.meu_barbeiro() is null or p_barbeiro is distinct from privado.meu_barbeiro() then
      raise exception 'Você só pode registrar atendimentos seus.' using errcode = '42501';
    end if;
  elsif not exists (select 1 from public.barbeiros where id = p_barbeiro and ativo) then
    raise exception 'Escolha um barbeiro ativo.' using errcode = 'P0001';
  end if;
  if p_data > privado.hoje() then
    raise exception 'O atendimento não pode ser numa data futura. Para isso, use o agendamento.' using errcode = 'P0001';
  end if;

  if v_cliente is null then
    if v_nome = '' then
      raise exception 'Escolha um cliente da lista ou preencha o nome do cliente novo.' using errcode = 'P0001';
    end if;
    v_cliente := privado.encontrar_ou_criar_cliente(v_barbearia, v_nome, trim(coalesce(p_novo_telefone, '')));
  end if;

  insert into public.atendimentos (barbearia_id, cliente_id, barbeiro_id, data, observacoes)
  values (v_barbearia, v_cliente, p_barbeiro, p_data, coalesce(p_observacoes, ''))
  returning id into v_id;
  return jsonb_build_object('id', v_id, 'cliente_id', v_cliente, 'data', p_data, 'barbeiro_id', p_barbeiro);
end $$;

-- Troca os turnos da semana de um barbeiro numa transação só (apaga os
-- antigos e grava os novos). A RLS de horarios_trabalho decide se o
-- usuário pode: dono, ou o próprio barbeiro.
-- p_turnos: [{"dia_semana": 0, "inicio": "09:00", "fim": "12:00"}, ...]
create function public.salvar_semana(p_barbeiro bigint, p_turnos jsonb) returns void
language plpgsql security invoker set search_path = '' as $$
declare
  v_barbearia bigint;
begin
  select barbearia_id into v_barbearia from public.barbeiros where id = p_barbeiro;
  if v_barbearia is null then
    raise exception 'Barbeiro não encontrado.' using errcode = 'P0002';
  end if;
  delete from public.horarios_trabalho where barbeiro_id = p_barbeiro;
  insert into public.horarios_trabalho (barbearia_id, barbeiro_id, dia_semana, inicio, fim)
  select v_barbearia, p_barbeiro, t.dia_semana, t.inicio, t.fim
    from jsonb_to_recordset(p_turnos) as t (dia_semana smallint, inicio time, fim time);
end $$;

-- Números do balanço, contados pelo banco: o balanço de um ano custa o
-- mesmo que o de um dia. O papel "barbeiro" sempre vê só o próprio (o
-- parâmetro p_barbeiro é ignorado para ele); sem ficha ligada, nada.
create function public.balanco_numeros(p_inicio date, p_fim date, p_barbeiro bigint default null) returns jsonb
language plpgsql stable security invoker set search_path = '' as $$
declare
  v_barbeiro bigint := p_barbeiro;
begin
  if privado.meu_papel() = 'barbeiro' then
    v_barbeiro := privado.meu_barbeiro();
    if v_barbeiro is null then
      return null;
    end if;
  end if;

  return (
    with at as (
      select * from public.atendimentos
       where data between p_inicio and p_fim
         and (v_barbeiro is null or barbeiro_id = v_barbeiro)
    ),
    ag as (
      select status from public.agendamentos
       where privado.dia_local(inicio) between p_inicio and p_fim
         and (v_barbeiro is null or barbeiro_id = v_barbeiro)
    )
    select jsonb_build_object(
      'barbeiro_id', v_barbeiro,
      'quantidade', (select count(*) from at),
      'clientes', (select count(distinct cliente_id) from at),
      'faltas', (select count(*) from ag where status = 'faltou'),
      'cancelados', (select count(*) from ag where status = 'cancelado'),
      'por_dia', coalesce((select jsonb_object_agg(data, n) from (select data, count(*) as n from at group by data) x), '{}'),
      'por_mes', coalesce((select jsonb_object_agg(mes, n) from (
                   select to_char(data, 'YYYY-MM') as mes, count(*) as n from at group by 1) x), '{}'),
      'por_barbeiro', coalesce((
        select jsonb_agg(jsonb_build_object('barbeiro_id', x.barbeiro_id, 'nome', x.nome, 'quantidade', x.n)
                         order by x.n desc, x.nome)
          from (select at.barbeiro_id, br.nome, count(*) as n
                  from at left join public.barbeiros br on br.id = at.barbeiro_id
                 group by at.barbeiro_id, br.nome) x), '[]')
    )
  );
end $$;

-- ---------------------------------------------------------------------
-- Quem pode chamar o quê
-- ---------------------------------------------------------------------
-- O Postgres deixa qualquer um executar funções novas (grant to public).
-- Tiramos isso e liberamos só o necessário.
revoke execute on all functions in schema public from public, anon;
revoke execute on all functions in schema privado from public, anon;
alter default privileges in schema public revoke execute on functions from public, anon;

grant execute on function public.agenda_publica(text, bigint, bigint, date) to anon, authenticated;
grant execute on function public.agendar_online(text, bigint, bigint, timestamptz, text, text) to anon, authenticated;
grant execute on function public.confirmacao_publica(text, uuid) to anon, authenticated;
grant execute on function public.barbearia_publica(text) to anon, authenticated;

grant execute on function public.formato_internacional(text) to authenticated;
grant execute on function public.concluir_agendamento(bigint) to authenticated;
grant execute on function public.registrar_atendimento(bigint, text, text, bigint, date, text) to authenticated;
grant execute on function public.salvar_semana(bigint, jsonb) to authenticated;
grant execute on function public.balanco_numeros(date, date, bigint) to authenticated;
-- Usadas por dentro das funções acima, que rodam como o usuário.
grant execute on all functions in schema privado to authenticated;
