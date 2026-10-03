/**
 * Regras do app que não dependem do banco (testes de balanço, ausências e telefones da versão Django, adaptados).
 */
import { describe, expect, test } from 'vitest'
import { ausenteEm, descreverAusencia, mensagemAusencia, mensagemLembrete, situacaoNoDia } from '../lib/agenda'
import { diaDaSemana, diaLocal, horaLocal, instante, lerDia, lerHora } from '../lib/datas'
import { daUrl, deslocar, diasDecorridos, doTipo, MAXIMO_DIAS, paraComparar, quantidadeDeDias, variacao } from '../lib/periodo'
import { formatoInternacional, linkWhatsapp, mesmoTelefone } from '../lib/telefones'
import type { Ausencia, HorarioTrabalho } from '../lib/tipos'

describe('datas no fuso de São Paulo (servidor em UTC)', () => {
  test('instante e volta', () => {
    const i = instante('2026-10-05', '22:30')
    expect(i.toISOString()).toBe('2026-10-06T01:30:00.000Z')
    expect(diaLocal(i)).toBe('2026-10-05')
    expect(horaLocal(i)).toBe('22:30')
  })
  test('dia da semana começa na segunda (0)', () => {
    expect(diaDaSemana('2026-10-05')).toBe(0)
    expect(diaDaSemana('2026-10-11')).toBe(6)
  })
  test('entrada inválida vira null', () => {
    expect(lerDia('2026-02-30')).toBeNull()
    expect(lerDia('ontem')).toBeNull()
    expect(lerHora('25:00')).toBeNull()
    expect(lerHora('09:15:00')).toBe('09:15')
  })
})

describe('período do balanço', () => {
  test('semana vai de segunda a domingo', () => {
    expect(doTipo('semana', '2026-10-08')).toEqual({ tipo: 'semana', inicio: '2026-10-05', fim: '2026-10-11' })
  })
  test('mês anterior e seguinte', () => {
    const marco = doTipo('mes', '2026-03-15')
    expect(deslocar(marco, -1)).toEqual({ tipo: 'mes', inicio: '2026-02-01', fim: '2026-02-28' })
    expect(deslocar(marco, 1)).toEqual({ tipo: 'mes', inicio: '2026-04-01', fim: '2026-04-30' })
  })
  test('parâmetro inválido cai na semana atual', () => {
    expect(daUrl({ periodo: 'ano', data: 'xx' }, '2026-10-08')).toEqual(doTipo('semana', '2026-10-08'))
  })
  test('datas livres invertidas são corrigidas e faixa longa é cortada', () => {
    expect(daUrl({ periodo: 'livre', de: '2026-10-10', ate: '2026-10-01' }, '2026-10-08')).toMatchObject({ inicio: '2026-10-01', fim: '2026-10-10' })
    const longa = daUrl({ periodo: 'livre', de: '2020-01-01', ate: '2026-01-01' }, '2026-10-08')
    expect(quantidadeDeDias(longa)).toBe(MAXIMO_DIAS)
  })
  test('semana em andamento compara até o mesmo dia; encerrada, com a semana inteira', () => {
    const atual = doTipo('semana', '2026-10-07') // quarta
    expect(paraComparar(atual, '2026-10-07')).toEqual({ tipo: 'semana', inicio: '2026-09-28', fim: '2026-09-30' })
    expect(paraComparar(doTipo('semana', '2026-09-30'), '2026-10-07')).toEqual({ tipo: 'semana', inicio: '2026-09-21', fim: '2026-09-27' })
    expect(paraComparar(doTipo('semana', '2026-10-20'), '2026-10-07')).toBeNull()
  })
  test('variação e dias decorridos', () => {
    expect(variacao(12, 10)).toBe(20)
    expect(variacao(5, 0)).toBeNull()
    expect(diasDecorridos(doTipo('semana', '2026-10-07'), '2026-10-07')).toBe(3)
  })
})

describe('equipe do dia e ausências', () => {
  const turno = (dia: number, inicio: string, fim: string): HorarioTrabalho => ({ id: 1, barbeiro_id: 1, dia_semana: dia, inicio, fim })
  const ausencia = (extra: Partial<Ausencia>): Ausencia => ({
    id: 1, barbeiro_id: 1, data_inicio: '2026-10-05', data_fim: '2026-10-05', hora_inicio: null, hora_fim: null, motivo: '', ...extra,
  })
  const horarios = [turno(0, '09:00:00', '12:00:00'), turno(0, '13:00:00', '19:00:00')]

  test('atendendo, parcial, ausente e sem expediente', () => {
    expect(situacaoNoDia(horarios, [], '2026-10-05')).toMatchObject({ situacao: 'atendendo', texto: '09:00–12:00, 13:00–19:00' })
    expect(situacaoNoDia(horarios, [ausencia({ hora_inicio: '15:00:00', hora_fim: '23:59:00' })], '2026-10-05')).toMatchObject({
      situacao: 'parcial',
      texto: '09:00–12:00, 13:00–19:00 · ausente 15:00–23:59',
    })
    const ferias = ausencia({ data_fim: '2026-10-12', motivo: 'Férias' })
    expect(situacaoNoDia(horarios, [ferias], '2026-10-05')).toMatchObject({ situacao: 'ausente', texto: 'Ausente até 12/10 · Férias', desfazer: [] })
    expect(situacaoNoDia(horarios, [], '2026-10-06')).toMatchObject({ situacao: 'folga' })
  })

  test('ausente em um trecho do dia', () => {
    const parcial = [ausencia({ hora_inicio: '13:00:00', hora_fim: '18:00:00' })]
    expect(ausenteEm(parcial, 1, instante('2026-10-05', '17:45'), instante('2026-10-05', '18:15'))).toBe(true)
    expect(ausenteEm(parcial, 1, instante('2026-10-05', '18:00'), instante('2026-10-05', '18:30'))).toBe(false)
    expect(ausenteEm(parcial, 2, instante('2026-10-05', '14:00'), instante('2026-10-05', '14:30'))).toBe(false)
  })

  test('descrição da ausência', () => {
    expect(descreverAusencia(ausencia({ hora_inicio: '13:00:00', hora_fim: '18:00:00' }))).toBe('05/10/2026, das 13:00 às 18:00')
    expect(descreverAusencia(ausencia({ data_fim: '2026-10-12' }))).toBe('05/10 a 12/10/2026')
  })
})

describe('telefones e WhatsApp', () => {
  test('código do Brasil e comparação ignorando formatação', () => {
    expect(formatoInternacional('(11) 98765-4321')).toBe('5511987654321')
    expect(formatoInternacional('9999')).toBe('')
    expect(mesmoTelefone('+55 11 98765-4321', '11987654321')).toBe(true)
    expect(mesmoTelefone('', '')).toBe(false)
  })
  test('link com a mensagem pronta; sem telefone, sem link', () => {
    expect(linkWhatsapp('11987654321', 'Olá, tudo bem?')).toBe('https://wa.me/5511987654321?text=Ol%C3%A1%2C%20tudo%20bem%3F')
    expect(linkWhatsapp('', 'oi')).toBe('')
  })
  test('mensagens prontas', () => {
    const dados = { barbearia: 'Barbearia do João', cliente: 'Carlos Silva', barbeiro: 'Pedro', servico: 'Corte', inicio: instante('2026-10-05', '14:00') }
    expect(mensagemLembrete(dados)).toBe('Olá, Carlos! Lembrando do seu horário na Barbearia do João: 05/10 às 14:00, corte com Pedro.')
    expect(mensagemAusencia(dados)).toContain('O Pedro não vai poder atender no seu horário de 05/10 às 14:00.')
  })
})
