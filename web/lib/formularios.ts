/**
 * Apoio aos formulários com validação (useActionState do React).
 *
 * A ação do servidor recebe o FormData, valida e devolve um
 * EstadoFormulario: erros por campo, um erro geral e os valores
 * digitados, para o formulário voltar preenchido quando há erro.
 */
export interface EstadoFormulario {
  erro?: string
  erros?: Record<string, string>
  valores?: Record<string, string>
  /** Mensagem de sucesso quando a ação não muda de página. */
  ok?: string
  /** Campo livre para casos especiais (ex.: o link gerado no painel). */
  extra?: Record<string, string | boolean>
}

export const ESTADO_INICIAL: EstadoFormulario = {}

export function texto(dados: FormData, nome: string): string {
  const v = dados.get(nome)
  return typeof v === 'string' ? v.trim() : ''
}

export function inteiro(dados: FormData, nome: string): number | null {
  const v = texto(dados, nome)
  return /^\d+$/.test(v) ? Number(v) : null
}

export function marcado(dados: FormData, nome: string): boolean {
  return dados.get(nome) === 'on'
}

export function valores(dados: FormData): Record<string, string> {
  const saida: Record<string, string> = {}
  for (const [chave, valor] of dados.entries()) {
    if (typeof valor === 'string' && !chave.startsWith('$')) saida[chave] = valor
  }
  return saida
}

export const EMAIL_VALIDO = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
