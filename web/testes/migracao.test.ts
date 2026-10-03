/**
 * Ensaio da migração Django -> Supabase num banco em memória: tabelas do
 * Django (só as colunas usadas) com dados de exemplo, a cópia, e as
 * conferências de que tudo chegou e de que a RLS vale para os dados copiados.
 */
import { beforeAll, describe, expect, test } from 'vitest'
import { copiarDados } from '../scripts/copiar-dados'
import { type Banco, comoAdmin, comoUsuario, criarBanco, linhas, valor } from './banco'

const DJANGO = `
  create table contas_barbearia (id bigint primary key, nome text, slug text, telefone text, endereco text, agendamento_online bool, criado_em timestamptz);
  create table contas_usuario (id bigint primary key, username text, email text, first_name text, last_name text, is_superuser bool, is_active bool,
    date_joined timestamptz, papel text, barbearia_id bigint);
  create table cadastros_barbeiro (id bigint primary key, barbearia_id bigint, nome text, telefone text, ativo bool, usuario_id bigint,
    criado_em timestamptz, atualizado_em timestamptz);
  create table cadastros_servico (id bigint primary key, barbearia_id bigint, nome text, preco numeric(8,2), duracao_minutos int, ativo bool,
    criado_em timestamptz, atualizado_em timestamptz);
  create table cadastros_cliente (id bigint primary key, barbearia_id bigint, nome text, telefone text, email text, data_nascimento date,
    endereco text, observacoes text, criado_em timestamptz, atualizado_em timestamptz);
  create table cadastros_horariotrabalho (id bigint primary key, barbeiro_id bigint, dia_semana int, inicio time, fim time);
  create table cadastros_bloqueio (id bigint primary key, barbeiro_id bigint, data_inicio date, data_fim date, hora_inicio time, hora_fim time, motivo text);
  create table agenda_agendamento (id bigint primary key, barbearia_id bigint, cliente_id bigint, barbeiro_id bigint, servico_id bigint,
    inicio timestamptz, fim timestamptz, status text, observacoes text, criado_em timestamptz, atualizado_em timestamptz);
  create table agenda_atendimento (id bigint primary key, barbearia_id bigint, cliente_id bigint, barbeiro_id bigint, agendamento_id bigint,
    data date, observacoes text, criado_em timestamptz, atualizado_em timestamptz);
  create table agenda_itematendimento (id bigint primary key, atendimento_id bigint, servico_id bigint, descricao text, valor numeric(8,2));
  create table contas_inscricaopush (id bigint primary key, usuario_id bigint, endpoint text, p256dh text, auth text, navegador text, criado_em timestamptz);

  insert into contas_barbearia values (7, 'Barbearia do João', 'Barbearia_do_Joao', '11 3333-4444', 'Rua A', true, now());
  insert into contas_usuario values
    (1, 'henry', 'henry@exemplo.com', 'Henry', '', true, true, now(), 'dono', null),
    (2, 'joao', 'joao@exemplo.com', 'João', 'Silva', false, true, now(), 'dono', 7),
    (3, 'pedro', 'pedro@exemplo.com', '', '', false, true, now(), 'barbeiro', 7);
  insert into cadastros_barbeiro values (4, 7, 'Pedro', '', true, 3, now(), now()), (5, 7, 'Zé', '', false, 1, now(), now());
  insert into cadastros_servico values (9, 7, 'Corte', 40, 30, true, now(), now());
  insert into cadastros_cliente values (15, 7, 'Carlos', '(11) 98765-4321', '', '1990-10-05', '', '', now(), now());
  insert into cadastros_horariotrabalho values (1, 4, 0, '09:00', '12:00');
  insert into cadastros_bloqueio values (1, 4, '2026-10-05', '2026-10-05', '13:00', '18:00', 'Consulta');
  insert into agenda_agendamento values
    (20, 7, 15, 4, 9, '2026-10-01 14:00-03', '2026-10-01 14:30-03', 'concluido', '', now(), now()),
    (21, 7, 15, 4, 9, '2026-10-20 14:00-03', '2026-10-20 14:30-03', 'agendado', '', now(), now());
  insert into agenda_atendimento values (30, 7, 15, 4, 20, '2026-10-01', '', now(), now());
  insert into agenda_itematendimento values (40, 30, 9, 'Corte', 35);
  insert into contas_inscricaopush values (1, 3, 'https://push.exemplo/abc', 'k', 'a', 'Chrome', now());
`

const UUID = { henry: '00000000-0000-0000-0000-000000000001', joao: '00000000-0000-0000-0000-000000000002', pedro: '00000000-0000-0000-0000-000000000003' }
let db: Banco
let contagens: Record<string, number>

beforeAll(async () => {
  db = await criarBanco()
  await db.exec(DJANGO)
  await db.exec(`insert into auth.users (id) values ('${UUID.henry}'), ('${UUID.joao}'), ('${UUID.pedro}')`)
  const q = async (sql: string, params?: unknown[]) => (await db.query(sql, params)).rows
  await db.exec('begin')
  contagens = await copiarDados(q, [
    { djangoId: 1, uuid: UUID.henry },
    { djangoId: 2, uuid: UUID.joao },
    { djangoId: 3, uuid: UUID.pedro },
  ])
  await db.exec('commit')
}, 120_000)

describe('migração do Django', () => {
  test('todos os dados chegam, com os mesmos ids', () => {
    expect(contagens).toMatchObject({
      barbearias: 1, perfis: 3, barbeiros: 2, servicos: 1, clientes: 1, horarios_trabalho: 1, ausencias: 1,
      agendamentos: 2, atendimentos: 1, itens_atendimento: 1, inscricoes_push: 1,
    })
  })

  test('endereço normalizado, perfis com nome e papel, superadmin preservado', async () => {
    expect(await valor(db, 'select slug from barbearias where id = 7')).toBe('barbearia-do-joao')
    expect(await linhas(db, 'select nome, papel, superadmin from perfis order by nome')).toEqual([
      { nome: 'Henry', papel: 'dono', superadmin: true },
      { nome: 'João Silva', papel: 'dono', superadmin: false },
      { nome: 'pedro', papel: 'barbeiro', superadmin: false },
    ])
  })

  test('login de outra barbearia não fica ligado ao barbeiro', async () => {
    expect(await linhas(db, 'select id, usuario_id from barbeiros order by id')).toEqual([
      { id: 4, usuario_id: UUID.pedro },
      { id: 5, usuario_id: null },
    ])
  })

  test('o preço pago no histórico é mantido e o próximo id continua depois do maior', async () => {
    expect(await valor(db, 'select valor from itens_atendimento where id = 40')).toBe('35.00')
    const novo = await valor<number>(db, `insert into clientes (barbearia_id, nome) values (7, 'Novo') returning id`)
    expect(novo).toBe(16)
  })

  test('a RLS vale para os dados migrados', async () => {
    await comoUsuario(db, UUID.pedro)
    expect(await valor(db, 'select count(*)::int from agendamentos')).toBe(2)
    expect(await valor(db, `select nome from clientes where id = 15`)).toBe('Carlos')
    await comoUsuario(db, UUID.henry) // superadmin sem barbearia: não vê dados de barbearias
    expect(await valor(db, 'select count(*)::int from clientes')).toBe(0)
    await comoAdmin(db)
  })
})
