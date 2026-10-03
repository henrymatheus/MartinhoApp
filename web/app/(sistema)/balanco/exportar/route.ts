import type { NextRequest } from 'next/server'
import { escopoDoBalanco, listaDoPeriodo } from '@/lib/balanco'
import { ddmmaaaa, hojeLocal, horaLocal } from '@/lib/datas'
import { daUrl } from '@/lib/periodo'
import { obterSessao, type SessaoDaBarbearia } from '@/lib/sessao'

/**
 * Evita que um nome como "=HIPERLINK(...)" vire fórmula ao abrir no Excel.
 * O nome do cliente pode vir da página pública, digitado por qualquer um.
 */
function celulaSegura(valor: string) {
  const texto = /^[=+\-@]/.test(valor) ? `'${valor}` : valor
  return /[;"\n\r]/.test(texto) ? `"${texto.replace(/"/g, '""')}"` : texto
}

/**
 * O período em CSV, com a mesma regra de acesso da tela. Ponto e vírgula,
 * no padrão do Excel em português; o BOM no início faz o Excel ler os
 * acentos corretamente. Na planilha, ordem cronológica.
 */
export async function GET(pedido: NextRequest) {
  const sessao = await obterSessao()
  if (!sessao?.barbearia) return new Response('Faça login.', { status: 401 })
  const parametros = Object.fromEntries(pedido.nextUrl.searchParams)
  const periodo = daUrl(parametros, hojeLocal())
  const escopo = await escopoDoBalanco(sessao as SessaoDaBarbearia, parametros.barbeiro)
  if (escopo.semVinculo) return new Response('Não encontrado', { status: 404 })

  const lista = await listaDoPeriodo(sessao as SessaoDaBarbearia, periodo, escopo.barbeiro?.id ?? null, 100_000)
  const linhas = [['Data', 'Horário', 'Cliente', 'Barbeiro', 'Observações']]
  for (const at of [...lista].reverse()) {
    linhas.push([
      ddmmaaaa(at.data),
      at.agendamento ? horaLocal(at.agendamento.inicio) : 'sem horário',
      celulaSegura(at.cliente.nome),
      celulaSegura(at.barbeiro?.nome ?? '—'),
      celulaSegura(at.observacoes),
    ])
  }
  const csv = '﻿' + linhas.map((l) => l.join(';')).join('\r\n') + '\r\n'
  return new Response(csv, {
    headers: {
      'Content-Type': 'text/csv; charset=utf-8',
      'Content-Disposition': `attachment; filename="balanco-${periodo.inicio}-a-${periodo.fim}.csv"`,
    },
  })
}
