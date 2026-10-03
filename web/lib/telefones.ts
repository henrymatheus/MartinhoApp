/**
 * Telefones brasileiros: normalização e links do WhatsApp.
 * Mesma regra de public.formato_internacional() no banco e da
 * versão Django.
 */

/** '(11) 98765-4321' -> '11987654321' */
export function somenteDigitos(telefone: string | null | undefined): string {
  return (telefone ?? '').replace(/\D/g, '')
}

/**
 * Dígitos com o código do Brasil (55), ou '' se o número estiver
 * incompleto. Telefones com DDD (10 ou 11 dígitos) ganham o 55 na frente.
 */
export function formatoInternacional(telefone: string | null | undefined): string {
  let digitos = somenteDigitos(telefone)
  if (digitos.length === 10 || digitos.length === 11) digitos = '55' + digitos
  return digitos.length >= 12 ? digitos : ''
}

/**
 * Link wa.me que abre uma conversa com esse número, com a mensagem pronta.
 * Não usa nenhuma API paga: o link só abre o WhatsApp de quem clicou.
 */
export function linkWhatsapp(telefone: string | null | undefined, mensagem = ''): string {
  const numero = formatoInternacional(telefone)
  return numero ? `https://wa.me/${numero}?text=${encodeURIComponent(mensagem)}` : ''
}

export function mesmoTelefone(a: string, b: string): boolean {
  const x = formatoInternacional(a)
  return x !== '' && x === formatoInternacional(b)
}

export function primeiroNome(nome: string): string {
  return nome.trim().split(/\s+/)[0] ?? ''
}
