/* eslint-disable @typescript-eslint/no-explicit-any -- respostas em JSON das funções do banco */
/**
 * Testes das regras que vivem no banco: tabelas, RLS e funções.
 * Equivalem aos testes da versão Django (no histórico do git), mais os de
 * isolamento por RLS, que lá não existiam (o filtro era feito nas telas).
 *
 * Cada teste roda dentro de uma transação desfeita no final, então um
 * teste não enxerga o que o outro gravou.
 */
import { afterEach, beforeAll, beforeEach, describe, expect, test } from 'vitest'
import { type Banco, comoAdmin, comoUsuario, comoVisitante, criarBanco, linhas, valor } from './banco'
import { hojeLocal, somarDias } from '../lib/datas'

let db: Banco

const U = {
  donoA: '00000000-0000-0000-0000-00000000000a',
  barbeiroA: '00000000-0000-0000-0000-0000000000ba',
  semFichaA: '00000000-0000-0000-0000-0000000000ca',
  donoB: '00000000-0000-0000-0000-00000000000b',
}
// ids fixos para os testes ficarem legíveis
const A = 1, B = 2
const JOAO = 1, PEDRO = 2, ZE = 3
const CORTE = 1, BARBA = 2, CORTE_B = 3
const CLIENTE_A = 1, CLIENTE_B = 2

/** Uma segunda-feira daqui a pelo menos 3 dias (longe da antecedência mínima). */
function proximaSegunda() {
  let dia = somarDias(hojeLocal(), 3)
  while (new Date(`${dia}T12:00:00Z`).getUTCDay() !== 1) dia = somarDias(dia, 1)
  return dia
}
const SEG = proximaSegunda()
const TER = somarDias(SEG, 1)
const DOM = somarDias(SEG, 6)
/** Instante em São Paulo (UTC-3, sem horário de verão desde 2019). */
const em = (dia: string, hora: string) => `${dia}T${hora}:00-03:00`

async function agendar(barbeiro: number, servico: number, inicio: string, extra = '') {
  return valor<number>(
    db,
    `insert into agendamentos (barbearia_id, cliente_id, barbeiro_id, servico_id, inicio${extra ? ', status' : ''})
     values ($1, $2, $3, $4, $5${extra ? `, '${extra}'` : ''}) returning id`,
    [barbeiro === ZE ? B : A, barbeiro === ZE ? CLIENTE_B : CLIENTE_A, barbeiro, servico, inicio],
  )
}

/** Espera um erro do Postgres com o código dado, sem estragar a transação do teste. */
async function esperarErro(sql: string, params: unknown[], codigo: string) {
  await db.exec('savepoint antes_do_erro')
  try {
    await expect(db.query(sql, params)).rejects.toMatchObject({ code: codigo })
  } finally {
    await db.exec('rollback to savepoint antes_do_erro')
  }
}

beforeAll(async () => {
  db = await criarBanco()
  await db.exec(`
    insert into auth.users (id) values ('${U.donoA}'), ('${U.barbeiroA}'), ('${U.semFichaA}'), ('${U.donoB}');
    insert into barbearias (id, nome, slug, telefone) values
      (${A}, 'Barbearia do João', 'barbearia-do-joao', '(11) 3333-4444'),
      (${B}, 'Outra Barbearia', 'outra', '');
    insert into perfis (id, barbearia_id, papel, nome) values
      ('${U.donoA}', ${A}, 'dono', 'Dono A'),
      ('${U.barbeiroA}', ${A}, 'barbeiro', 'João'),
      ('${U.semFichaA}', ${A}, 'barbeiro', 'Sem ficha'),
      ('${U.donoB}', ${B}, 'dono', 'Dono B');
    insert into barbeiros (id, barbearia_id, nome, usuario_id) values
      (${JOAO}, ${A}, 'João', '${U.barbeiroA}'), (${PEDRO}, ${A}, 'Pedro', null), (${ZE}, ${B}, 'Zé', null);
    insert into servicos (id, barbearia_id, nome, preco, duracao_minutos) values
      (${CORTE}, ${A}, 'Corte', 40, 30), (${BARBA}, ${A}, 'Barba', 25, 20), (${CORTE_B}, ${B}, 'Corte', 35, 30);
    insert into clientes (id, barbearia_id, nome, telefone) values
      (${CLIENTE_A}, ${A}, 'Carlos', '(11) 98765-4321'), (${CLIENTE_B}, ${B}, 'Bruno', '(21) 99999-0000');
    -- João: segunda a sábado, 09-12 e 13-19 (almoço 12-13). Pedro: segunda a sexta, 09-18. Zé: segunda a sábado.
    insert into horarios_trabalho (barbearia_id, barbeiro_id, dia_semana, inicio, fim)
      select ${A}, ${JOAO}, d, '09:00'::time, '12:00'::time from generate_series(0, 5) d
      union all select ${A}, ${JOAO}, d, '13:00', '19:00' from generate_series(0, 5) d
      union all select ${A}, ${PEDRO}, d, '09:00', '18:00' from generate_series(0, 4) d
      union all select ${B}, ${ZE}, d, '09:00', '18:00' from generate_series(0, 5) d;
  `)
  // Os ids acima foram fixados à mão; o próximo id automático começa depois deles.
  for (const t of ['barbearias', 'barbeiros', 'servicos', 'clientes']) {
    await db.exec(`select setval(pg_get_serial_sequence('${t}', 'id'), (select max(id) from ${t}))`)
  }
}, 120_000)

beforeEach(async () => {
  await db.exec('begin')
})
afterEach(async () => {
  await db.exec('rollback')
  await comoAdmin(db)
})

describe('conflito de horário (exclusion constraint)', () => {
  test('fim é calculado pela duração do serviço', async () => {
    const id = await agendar(JOAO, CORTE, em(SEG, '14:00'))
    const fim = await valor<Date>(db, 'select fim from agendamentos where id = $1', [id])
    expect(fim).toEqual(new Date(em(SEG, '14:30')))
  })

  test('recusa horários sobrepostos do mesmo barbeiro', async () => {
    await agendar(JOAO, CORTE, em(SEG, '14:00'))
    await esperarErro(
      `insert into agendamentos (barbearia_id, cliente_id, barbeiro_id, servico_id, inicio) values (1, 1, 1, 1, $1)`,
      [em(SEG, '14:15')],
      '23P01',
    )
  })

  test('novo agendamento que engloba outro conflita', async () => {
    await agendar(JOAO, BARBA, em(SEG, '14:05'))
    await esperarErro(
      `insert into agendamentos (barbearia_id, cliente_id, barbeiro_id, servico_id, inicio) values (1, 1, 1, 1, $1)`,
      [em(SEG, '14:00')],
      '23P01',
    )
  })

  test('horários encostados, barbeiros diferentes e cancelados não conflitam', async () => {
    await agendar(JOAO, CORTE, em(SEG, '14:00'))
    await agendar(JOAO, CORTE, em(SEG, '14:30'))
    await agendar(PEDRO, CORTE, em(SEG, '14:00'))
    await agendar(JOAO, CORTE, em(SEG, '16:00'), 'cancelado')
    await agendar(JOAO, CORTE, em(SEG, '16:00'))
    expect(await valor(db, 'select count(*)::int from agendamentos')).toBe(5)
  })

  test('editar o próprio agendamento não conflita com ele mesmo; remarcar recalcula o fim', async () => {
    const id = await agendar(JOAO, CORTE, em(SEG, '14:00'))
    await db.query(`update agendamentos set observacoes = 'chega atrasado' where id = $1`, [id])
    await db.query(`update agendamentos set inicio = $2, servico_id = ${BARBA} where id = $1`, [id, em(SEG, '15:00')])
    const fim = await valor<Date>(db, 'select fim from agendamentos where id = $1', [id])
    expect(fim).toEqual(new Date(em(SEG, '15:20')))
  })

  test('fim antes do início é recusado', async () => {
    await esperarErro(
      `insert into agendamentos (barbearia_id, cliente_id, barbeiro_id, servico_id, inicio, fim) values (1, 1, 1, 1, $1, $2)`,
      [em(SEG, '14:00'), em(SEG, '13:00')],
      '23514',
    )
  })
})

describe('integridade entre barbearias (chaves compostas)', () => {
  test('cliente de outra barbearia é recusado', async () => {
    await esperarErro(
      `insert into agendamentos (barbearia_id, cliente_id, barbeiro_id, servico_id, inicio) values (1, $1, 1, 1, $2)`,
      [CLIENTE_B, em(SEG, '14:00')],
      '23503',
    )
  })

  test('login de outra barbearia não pode ser ligado ao barbeiro', async () => {
    await esperarErro(`update barbeiros set usuario_id = $1 where id = ${PEDRO}`, [U.donoB], '23503')
  })
})

describe('histórico', () => {
  test('item copia nome e preço do serviço, e o reajuste não altera o histórico', async () => {
    const at = await valor<number>(db, `insert into atendimentos (barbearia_id, cliente_id, barbeiro_id) values (1, 1, 1) returning id`)
    await db.query(`insert into itens_atendimento (barbearia_id, atendimento_id, servico_id) values (1, $1, ${CORTE})`, [at])
    await db.query(`update servicos set preco = 50 where id = ${CORTE}`)
    const [item] = await linhas(db, 'select descricao, valor from itens_atendimento where atendimento_id = $1', [at])
    expect(item).toEqual({ descricao: 'Corte', valor: '40.00' })
  })
})

describe('ausências', () => {
  test('horário incompleto ou parcial em vários dias é recusado', async () => {
    await esperarErro(
      `insert into ausencias (barbearia_id, barbeiro_id, data_inicio, data_fim, hora_inicio) values (1, 1, $1, $1, '13:00')`,
      [SEG],
      '23514',
    )
    await esperarErro(
      `insert into ausencias (barbearia_id, barbeiro_id, data_inicio, data_fim, hora_inicio, hora_fim) values (1, 1, $1, $2, '13:00', '15:00')`,
      [SEG, TER],
      '23514',
    )
  })
})

describe('RLS: cada barbearia só vê e altera o que é seu', () => {
  test('visitante sem login não lê nenhuma tabela', async () => {
    await comoVisitante(db)
    for (const tabela of ['clientes', 'agendamentos', 'barbeiros', 'perfis', 'barbearias']) {
      await esperarErro(`select * from ${tabela}`, [], '42501')
    }
  })

  test('dono vê só os clientes e agendamentos da própria barbearia', async () => {
    await agendar(ZE, CORTE_B, em(SEG, '10:00'))
    await agendar(JOAO, CORTE, em(SEG, '10:00'))
    await comoUsuario(db, U.donoA)
    expect(await linhas(db, 'select nome from clientes')).toEqual([{ nome: 'Carlos' }])
    expect(await valor(db, 'select count(*)::int from agendamentos')).toBe(1)
    expect(await linhas(db, 'select nome from barbearias')).toEqual([{ nome: 'Barbearia do João' }])
  })

  test('não grava nem altera dados de outra barbearia', async () => {
    const id = await agendar(ZE, CORTE_B, em(SEG, '10:00'))
    await comoUsuario(db, U.donoA)
    await esperarErro(`insert into clientes (barbearia_id, nome) values (${B}, 'Intruso')`, [], '42501')
    const r = await db.query(`update agendamentos set status = 'cancelado' where id = $1`, [id])
    expect(r.affectedRows).toBe(0)
  })

  test('barbeiro não cadastra serviços nem barbeiros; o dono cadastra', async () => {
    await comoUsuario(db, U.barbeiroA)
    await esperarErro(`insert into servicos (barbearia_id, nome, preco) values (${A}, 'Pezinho', 10)`, [], '42501')
    await comoUsuario(db, U.donoA)
    await db.query(`insert into servicos (barbearia_id, nome, preco) values (${A}, 'Pezinho', 10)`)
  })

  test('barbeiro edita só os próprios horários e ausências', async () => {
    await comoUsuario(db, U.barbeiroA)
    await db.query(`select salvar_semana(${JOAO}, '[{"dia_semana": 0, "inicio": "10:00", "fim": "12:00"}]')`)
    await esperarErro(`select salvar_semana(${PEDRO}, '[{"dia_semana": 0, "inicio": "10:00", "fim": "12:00"}]')`, [], '42501')
    await esperarErro(
      `insert into ausencias (barbearia_id, barbeiro_id, data_inicio, data_fim) values (${A}, ${PEDRO}, $1, $1)`,
      [SEG],
      '42501',
    )
    await comoUsuario(db, U.semFichaA)
    await esperarErro(
      `insert into ausencias (barbearia_id, barbeiro_id, data_inicio, data_fim) values (${A}, ${JOAO}, $1, $1)`,
      [SEG],
      '42501',
    )
  })

  test('ninguém muda o próprio papel ou barbearia pela API', async () => {
    await comoUsuario(db, U.barbeiroA)
    const r = await db.query(`update perfis set papel = 'dono', barbearia_id = ${B} where id = $1`, [U.barbeiroA])
    expect(r.affectedRows).toBe(0)
  })

  test('cada um só vê os próprios aparelhos de aviso', async () => {
    await db.query(`insert into inscricoes_push (usuario_id, endpoint, p256dh, auth) values ($1, 'https://push/a', 'x', 'y')`, [U.donoA])
    await comoUsuario(db, U.barbeiroA)
    expect(await valor(db, 'select count(*)::int from inscricoes_push')).toBe(0)
  })
})

describe('horários livres', () => {
  const livres = (barbeiro: number, duracao: number, dia: string, agora = '2000-01-01T00:00:00Z') =>
    linhas<{ h: Date }>(db, 'select h from privado.horarios_livres($1, $2, $3, $4) h', [barbeiro, duracao, dia, agora]).then(
      (r) => r.map(({ h }) => h.toLocaleTimeString('pt-BR', { timeZone: 'America/Sao_Paulo', hour: '2-digit', minute: '2-digit' })),
    )

  test('dentro do expediente, fora do almoço e cabendo inteiro no turno', async () => {
    const h = await livres(JOAO, 30, SEG)
    expect(h[0]).toBe('09:00')
    expect(h).toContain('11:30')
    expect(h).not.toContain('11:45') // 11:45 + 30 min passa do fim do turno (12:00)
    expect(h).not.toContain('12:00')
    expect(h).toContain('13:00')
    expect(h.at(-1)).toBe('18:30')
  })

  test('agendamento existente ocupa o horário; cancelado não', async () => {
    await agendar(JOAO, CORTE, em(SEG, '10:00'))
    await agendar(JOAO, CORTE, em(SEG, '15:00'), 'cancelado')
    const h = await livres(JOAO, 30, SEG)
    expect(h).not.toContain('09:45')
    expect(h).not.toContain('10:00')
    expect(h).not.toContain('10:15')
    expect(h).toContain('10:30')
    expect(h).toContain('15:00')
  })

  test('folga zera o dia; ausência de parte do dia tira só o trecho', async () => {
    await db.query(`insert into ausencias (barbearia_id, barbeiro_id, data_inicio, data_fim) values (1, ${JOAO}, $1, $1)`, [SEG])
    expect(await livres(JOAO, 30, SEG)).toEqual([])
    await db.query(
      `insert into ausencias (barbearia_id, barbeiro_id, data_inicio, data_fim, hora_inicio, hora_fim) values (1, ${JOAO}, $1, $1, '13:00', '18:00')`,
      [TER],
    )
    const h = await livres(JOAO, 30, TER)
    expect(h).toContain('11:30')
    expect(h).not.toContain('13:00')
    expect(h).not.toContain('17:45')
    expect(h).toContain('18:00')
  })

  test('antecedência mínima de uma hora', async () => {
    const h = await livres(JOAO, 30, SEG, em(SEG, '09:50'))
    expect(h[0]).toBe('11:00')
  })

  test('dia sem turno não tem horário', async () => {
    expect(await livres(JOAO, 30, DOM)).toEqual([])
  })
})

describe('página pública de agendamento', () => {
  const agenda = (barbeiro: number | null = null, servico: number | null = null, dia: string | null = null, slug = 'barbearia-do-joao') =>
    valor<Record<string, any>>(db, 'select agenda_publica($1, $2, $3, $4)', [slug, barbeiro, servico, dia])
  const agendarOnline = (inicio: string, telefone = '11 91234-5678', nome = '  Ana   Souza ', servico = CORTE, barbeiro = JOAO) =>
    valor<Record<string, any>>(db, 'select agendar_online($1, $2, $3, $4, $5, $6)', ['barbearia-do-joao', barbeiro, servico, inicio, nome, telefone])

  beforeEach(async () => {
    await comoVisitante(db)
  })

  test('primeira tela mostra os barbeiros com o próximo horário, sem dados de clientes', async () => {
    const e = await agenda()
    expect(e!.barbearia).toMatchObject({ nome: 'Barbearia do João', whatsapp: '551133334444' })
    expect(e!.cartoes.map((c: any) => c.nome).sort()).toEqual(['João', 'Pedro'])
    expect(e!.cartoes.every((c: any) => c.proximo)).toBe(true)
    expect(JSON.stringify(e)).not.toContain('Carlos')
  })

  test('barbeiro ausente hoje aparece como ausente', async () => {
    await comoAdmin(db)
    await db.query(`insert into ausencias (barbearia_id, barbeiro_id, data_inicio, data_fim) values (1, ${PEDRO}, $1, $1)`, [hojeLocal()])
    await comoVisitante(db)
    const pedro = (await agenda())!.cartoes.find((c: any) => c.nome === 'Pedro')
    expect(pedro.situacao).toBe('Ausente hoje')
  })

  test('com barbeiro e serviço: dias e horários; dia de folga não aparece', async () => {
    await comoAdmin(db)
    await db.query(`insert into ausencias (barbearia_id, barbeiro_id, data_inicio, data_fim) values (1, ${JOAO}, $1, $1)`, [SEG])
    await comoVisitante(db)
    const e = (await agenda(JOAO, CORTE, TER))!
    expect(e.barbeiro.nome).toBe('João')
    expect(e.dias).not.toContain(SEG)
    expect(e.dias).not.toContain(DOM)
    expect(e.dia).toBe(TER)
    expect(e.horarios.length).toBeGreaterThan(10)
    // Dia inválido: abre no primeiro dia com horário.
    expect((await agenda(JOAO, CORTE, SEG))!.dia).toBe(e.dias[0])
  })

  test('agendamento online desligado ou endereço inexistente', async () => {
    expect(await agenda(null, null, null, 'nao-existe')).toBeNull()
    await comoAdmin(db)
    await db.query(`update barbearias set agendamento_online = false where id = ${A}`)
    await comoVisitante(db)
    expect(await agenda()).toBeNull()
    expect(await agendarOnline(em(SEG, '10:00'))).toEqual({ erro: 'pagina' })
  })

  test('agendar cria o cliente e o agendamento; o mesmo telefone vai para a mesma ficha', async () => {
    const r = await agendarOnline(em(SEG, '10:00'))
    expect(r).toMatchObject({ ok: true })
    const r2 = await agendarOnline(em(SEG, '11:00'), '+55 (11) 91234-5678', 'Ana')
    expect(r2).toMatchObject({ ok: true })
    await comoAdmin(db)
    const clientes = await linhas(db, `select nome from clientes where telefone_whatsapp = '5511912345678'`)
    expect(clientes).toEqual([{ nome: 'Ana Souza' }])
    // Cliente já cadastrado pela barbearia é reconhecido pelo telefone.
    await comoVisitante(db)
    await agendarOnline(em(SEG, '13:00'), '11987654321', 'Carlinhos')
    await comoAdmin(db)
    expect(await valor(db, `select count(*)::int from agendamentos where cliente_id = ${CLIENTE_A}`)).toBe(1)
  })

  test('horário ocupado, fora do expediente ou com telefone inválido não agenda', async () => {
    expect(await agendarOnline(em(SEG, '10:00'))).toMatchObject({ ok: true })
    expect(await agendarOnline(em(SEG, '10:15'), '11 90000-0000')).toEqual({ erro: 'ocupado' })
    expect(await agendarOnline(em(SEG, '12:00'), '11 90000-0000')).toEqual({ erro: 'ocupado' })
    expect(await agendarOnline(em(SEG, '10:07'), '11 90000-0000')).toEqual({ erro: 'ocupado' })
    expect(await agendarOnline(em(SEG, '15:00'), '9999')).toEqual({ erro: 'telefone' })
    expect(await agendarOnline(em(SEG, '15:00'), '11 90000-0000', '   ')).toEqual({ erro: 'nome' })
  })

  test('serviço ou barbeiro de outra barbearia não agenda', async () => {
    expect(await agendarOnline(em(SEG, '10:00'), undefined, undefined, CORTE_B)).toEqual({ erro: 'ocupado' })
    expect(await agendarOnline(em(SEG, '10:00'), undefined, undefined, CORTE, ZE)).toEqual({ erro: 'ocupado' })
  })

  test('no máximo 3 horários futuros por telefone', async () => {
    for (const hora of ['09:00', '10:00', '11:00']) expect(await agendarOnline(em(SEG, hora))).toMatchObject({ ok: true })
    expect(await agendarOnline(em(SEG, '14:00'))).toEqual({ erro: 'limite', maximo: 3 })
  })

  test('confirmação só abre com o código certo e a barbearia certa', async () => {
    const { codigo } = (await agendarOnline(em(SEG, '10:00')))!
    const c = await valor<Record<string, any>>(db, 'select confirmacao_publica($1, $2)', ['barbearia-do-joao', codigo])
    expect(c).toMatchObject({ servico: 'Corte', barbeiro: 'João', cliente: 'Ana Souza', status: 'agendado' })
    expect(await valor(db, 'select confirmacao_publica($1, $2)', ['outra', codigo])).toBeNull()
    expect(await valor(db, 'select confirmacao_publica($1, gen_random_uuid())', ['barbearia-do-joao'])).toBeNull()
  })

  test('visitante não chama as funções do sistema interno', async () => {
    await esperarErro('select concluir_agendamento(1)', [], '42501')
    await esperarErro(`select balanco_numeros(current_date, current_date)`, [], '42501')
  })
})

describe('concluir e registrar atendimento', () => {
  test('concluir registra no histórico com o serviço e o preço; não conclui duas vezes', async () => {
    const id = await agendar(JOAO, CORTE, em(SEG, '10:00'))
    await comoUsuario(db, U.donoA)
    await db.query('select concluir_agendamento($1)', [id])
    const [at] = await linhas(
      db,
      `select a.data::text, a.barbeiro_id, i.descricao, i.valor from atendimentos a join itens_atendimento i on i.atendimento_id = a.id where a.agendamento_id = $1`,
      [id],
    )
    expect(at).toEqual({ data: SEG, barbeiro_id: JOAO, descricao: 'Corte', valor: '40.00' })
    await esperarErro('select concluir_agendamento($1)', [id], 'P0001')
  })

  test('não conclui agendamento de outra barbearia', async () => {
    const id = await agendar(ZE, CORTE_B, em(SEG, '10:00'))
    await comoUsuario(db, U.donoA)
    await esperarErro('select concluir_agendamento($1)', [id], 'P0001')
  })

  const registrar = (cliente: number | null, nome: string, telefone: string, barbeiro: number, data = hojeLocal()) =>
    valor<Record<string, any>>(db, 'select registrar_atendimento($1, $2, $3, $4, $5, $6)', [cliente, nome, telefone, barbeiro, data, ''])

  test('registra; cliente novo com telefone já cadastrado vai para a ficha existente', async () => {
    await comoUsuario(db, U.donoA)
    expect(await registrar(CLIENTE_A, '', '', PEDRO)).toMatchObject({ cliente_id: CLIENTE_A })
    expect(await registrar(null, 'Carlos Silva', '11 98765-4321', PEDRO)).toMatchObject({ cliente_id: CLIENTE_A })
    const novo = await registrar(null, 'Sem Telefone', '', PEDRO)
    expect(novo!.cliente_id).not.toBe(CLIENTE_A)
  })

  test('exige cliente e recusa data futura', async () => {
    await comoUsuario(db, U.donoA)
    await esperarErro('select registrar_atendimento(null, $1, $2, $3, $4, $5)', ['  ', '', PEDRO, hojeLocal(), ''], 'P0001')
    await esperarErro('select registrar_atendimento($1, $2, $3, $4, $5, $6)', [CLIENTE_A, '', '', PEDRO, somarDias(hojeLocal(), 1), ''], 'P0001')
  })

  test('barbeiro registra só para si', async () => {
    await comoUsuario(db, U.barbeiroA)
    expect(await registrar(CLIENTE_A, '', '', JOAO)).toMatchObject({ barbeiro_id: JOAO })
    await esperarErro('select registrar_atendimento($1, $2, $3, $4, $5, $6)', [CLIENTE_A, '', '', PEDRO, hojeLocal(), ''], '42501')
  })
})

describe('balanço', () => {
  beforeEach(async () => {
    const ontem = somarDias(hojeLocal(), -1)
    await db.exec(`
      insert into atendimentos (barbearia_id, cliente_id, barbeiro_id, data) values
        (1, 1, ${JOAO}, '${ontem}'), (1, 1, ${JOAO}, '${ontem}'), (1, 1, ${PEDRO}, '${ontem}'),
        (2, 2, ${ZE}, '${ontem}');
      insert into clientes (barbearia_id, nome) values (1, 'Outro');
      insert into atendimentos (barbearia_id, cliente_id, barbeiro_id, data)
        values (1, (select max(id) from clientes), ${PEDRO}, '${somarDias(ontem, -1)}');
      insert into agendamentos (barbearia_id, cliente_id, barbeiro_id, servico_id, inicio, status) values
        (1, 1, ${JOAO}, 1, '${em(ontem, '10:00')}', 'faltou'),
        (1, 1, ${JOAO}, 1, '${em(ontem, '11:00')}', 'cancelado');
    `)
  })
  const numeros = (barbeiro: number | null = null) =>
    valor<Record<string, any>>(db, 'select balanco_numeros($1, $2, $3)', [somarDias(hojeLocal(), -6), hojeLocal(), barbeiro])

  test('contagens do período, sem misturar barbearias; faltas e cancelamentos à parte', async () => {
    await comoUsuario(db, U.donoA)
    const n = (await numeros())!
    expect(n).toMatchObject({ quantidade: 4, clientes: 2, faltas: 1, cancelados: 1 })
    expect(n.por_barbeiro).toEqual([
      { barbeiro_id: JOAO, nome: 'João', quantidade: 2 },
      { barbeiro_id: PEDRO, nome: 'Pedro', quantidade: 2 },
    ])
    expect(n.por_dia[somarDias(hojeLocal(), -1)]).toBe(3)
    expect((await numeros(PEDRO))!.quantidade).toBe(2)
  })

  test('barbeiro vê só o próprio, mesmo pedindo o de outro; sem ficha, nada', async () => {
    await comoUsuario(db, U.barbeiroA)
    expect(await numeros(PEDRO)).toMatchObject({ barbeiro_id: JOAO, quantidade: 2 })
    await comoUsuario(db, U.semFichaA)
    expect(await numeros()).toBeNull()
  })
})
