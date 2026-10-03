/**
 * A cópia dos dados das tabelas do Django para as tabelas novas, dentro
 * do mesmo banco (o Supabase de produção já guarda as duas).
 *
 * Fica separada do script principal (migrar-do-django.ts) para poder ser
 * testada num banco em memória (testes/migracao.test.ts) antes de rodar
 * em produção.
 *
 * Os ids são mantidos: o cliente 15 no Django continua sendo o 15. Assim
 * links antigos da ficha (/clientes/15) seguem funcionando. Os logins
 * mudam de id (o Supabase Auth usa uuid); `mapa` diz qual uuid substituiu
 * cada usuário do Django.
 */
export type Consulta = (sql: string, params?: unknown[]) => Promise<unknown[]>

export const TABELAS_NOVAS = [
  'barbearias',
  'barbeiros',
  'servicos',
  'clientes',
  'horarios_trabalho',
  'ausencias',
  'agendamentos',
  'atendimentos',
  'itens_atendimento',
  'inscricoes_push',
] as const

export async function copiarDados(q: Consulta, mapa: { djangoId: number; uuid: string }[]) {
  await q('create temp table mapa_usuarios (django_id bigint primary key, uuid uuid not null) on commit drop')
  for (const { djangoId, uuid } of mapa) await q('insert into mapa_usuarios values ($1, $2)', [djangoId, uuid])

  // O endereço (slug) passa a aceitar só letras minúsculas, números e hífens.
  await q(`
    insert into public.barbearias (id, nome, slug, telefone, endereco, agendamento_online, criado_em)
    select id, nome,
           coalesce(nullif(trim(both '-' from regexp_replace(lower(slug), '[^a-z0-9]+', '-', 'g')), ''), 'barbearia-' || id),
           telefone, endereco, agendamento_online, criado_em
      from contas_barbearia`)

  await q(`
    insert into public.perfis (id, barbearia_id, nome, papel, superadmin, criado_em)
    select m.uuid, u.barbearia_id,
           left(coalesce(nullif(trim(u.first_name || ' ' || u.last_name), ''), u.username), 120),
           u.papel, u.is_superuser, u.date_joined
      from contas_usuario u join mapa_usuarios m on m.django_id = u.id`)

  // O login só é ligado ao barbeiro se for da mesma barbearia (regra nova do banco).
  await q(`
    insert into public.barbeiros (id, barbearia_id, nome, telefone, ativo, usuario_id, criado_em, atualizado_em)
    select b.id, b.barbearia_id, b.nome, b.telefone, b.ativo,
           case when u.barbearia_id = b.barbearia_id then m.uuid end,
           b.criado_em, b.atualizado_em
      from cadastros_barbeiro b
      left join contas_usuario u on u.id = b.usuario_id
      left join mapa_usuarios m on m.django_id = b.usuario_id`)

  await q(`
    insert into public.servicos (id, barbearia_id, nome, preco, duracao_minutos, ativo, criado_em, atualizado_em)
    select id, barbearia_id, nome, preco, greatest(duracao_minutos, 5), ativo, criado_em, atualizado_em
      from cadastros_servico`)

  await q(`
    insert into public.clientes (id, barbearia_id, nome, telefone, email, data_nascimento, endereco, observacoes, criado_em, atualizado_em)
    select id, barbearia_id, coalesce(nullif(trim(nome), ''), 'Sem nome'), telefone, email, data_nascimento, endereco, observacoes,
           criado_em, atualizado_em
      from cadastros_cliente`)

  await q(`
    insert into public.horarios_trabalho (id, barbearia_id, barbeiro_id, dia_semana, inicio, fim)
    select h.id, b.barbearia_id, h.barbeiro_id, h.dia_semana, h.inicio, h.fim
      from cadastros_horariotrabalho h join cadastros_barbeiro b on b.id = h.barbeiro_id`)

  await q(`
    insert into public.ausencias (id, barbearia_id, barbeiro_id, data_inicio, data_fim, hora_inicio, hora_fim, motivo)
    select x.id, b.barbearia_id, x.barbeiro_id, x.data_inicio, x.data_fim, x.hora_inicio, x.hora_fim, x.motivo
      from cadastros_bloqueio x join cadastros_barbeiro b on b.id = x.barbeiro_id`)

  // codigo_publico (o código da página de confirmação) é gerado novo: os
  // links de confirmação antigos, assinados pelo Django, deixam de abrir.
  await q(`
    insert into public.agendamentos (id, barbearia_id, cliente_id, barbeiro_id, servico_id, inicio, fim, status, observacoes, criado_em, atualizado_em)
    select id, barbearia_id, cliente_id, barbeiro_id, servico_id, inicio, fim, status, observacoes, criado_em, atualizado_em
      from agenda_agendamento`)

  await q(`
    insert into public.atendimentos (id, barbearia_id, cliente_id, barbeiro_id, agendamento_id, data, observacoes, criado_em, atualizado_em)
    select id, barbearia_id, cliente_id, barbeiro_id, agendamento_id, data, observacoes, criado_em, atualizado_em
      from agenda_atendimento`)

  await q(`
    insert into public.itens_atendimento (id, barbearia_id, atendimento_id, servico_id, descricao, valor)
    select i.id, a.barbearia_id, i.atendimento_id, i.servico_id, coalesce(nullif(trim(i.descricao), ''), 'Serviço'), coalesce(i.valor, 0)
      from agenda_itematendimento i join agenda_atendimento a on a.id = i.atendimento_id`)

  await q(`
    insert into public.inscricoes_push (id, usuario_id, endpoint, p256dh, auth, navegador, criado_em)
    select p.id, m.uuid, p.endpoint, p.p256dh, p.auth, p.navegador, p.criado_em
      from contas_inscricaopush p join mapa_usuarios m on m.django_id = p.usuario_id`)

  // Os ids foram copiados à mão; o contador de cada tabela precisa
  // continuar depois do maior, senão o próximo cadastro repetiria um id.
  for (const tabela of TABELAS_NOVAS) {
    await q(`select setval(pg_get_serial_sequence('public.${tabela}', 'id'), coalesce((select max(id) from public.${tabela}), 0) + 1, false)`)
  }

  const contagens: Record<string, number> = {}
  for (const tabela of [...TABELAS_NOVAS, 'perfis']) {
    const [linha] = (await q(`select count(*)::int as n from public.${tabela}`)) as { n: number }[]
    contagens[tabela] = linha.n
  }
  return contagens
}
