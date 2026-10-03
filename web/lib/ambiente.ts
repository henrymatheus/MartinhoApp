/**
 * Variáveis de ambiente (arquivo .env.local no desenvolvimento, painel da
 * Vercel em produção). Falta de variável obrigatória vira um erro claro,
 * em vez de um "undefined" difícil de rastrear.
 */
const VALORES: Record<string, string | undefined> = {
  // As NEXT_PUBLIC_ precisam ser lidas pelo nome completo para o Next
  // conseguir embuti-las no código no momento do build.
  NEXT_PUBLIC_SUPABASE_URL: process.env.NEXT_PUBLIC_SUPABASE_URL,
  NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY: process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY,
  NEXT_PUBLIC_VAPID_PUBLIC_KEY: process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY,
}

export function variavel(nome: string): string {
  const valor = nome in VALORES ? VALORES[nome] : process.env[nome]
  if (!valor) throw new Error(`Variável de ambiente ${nome} não configurada. Veja web/.env.example.`)
  return valor
}

export function variavelOpcional(nome: string): string {
  return (nome in VALORES ? VALORES[nome] : process.env[nome]) ?? ''
}
