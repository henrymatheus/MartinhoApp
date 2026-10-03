import 'server-only'
import { cookies } from 'next/headers'

/**
 * Mensagens de uma tela para a próxima ("Agendado: Carlos às 14:00"),
 * como o messages do Django.
 *
 * A ação grava a mensagem num cookie de vida curta; a página seguinte lê
 * e mostra; o navegador apaga o cookie logo depois (ApagarAvisos).
 */
export const COOKIE_AVISOS = 'martinho_avisos'

export type TipoAviso = 'sucesso' | 'erro' | 'alerta'
export interface Aviso {
  tipo: TipoAviso
  texto: string
}

function decodificar(valor: string | undefined): Aviso[] {
  if (!valor) return []
  try {
    const lista = JSON.parse(decodeURIComponent(valor))
    return Array.isArray(lista) ? lista.filter((a) => typeof a?.texto === 'string') : []
  } catch {
    return []
  }
}

/** Só pode ser chamada dentro de uma Server Action. */
export async function avisar(tipo: TipoAviso, texto: string) {
  const loja = await cookies()
  const lista = [...decodificar(loja.get(COOKIE_AVISOS)?.value), { tipo, texto }]
  loja.set(COOKIE_AVISOS, encodeURIComponent(JSON.stringify(lista)), {
    path: '/',
    maxAge: 60,
    sameSite: 'lax',
    // O navegador precisa conseguir apagar o cookie depois de mostrar.
    httpOnly: false,
  })
}

export async function lerAvisos(): Promise<{ avisos: Aviso[]; bruto: string }> {
  const bruto = (await cookies()).get(COOKIE_AVISOS)?.value ?? ''
  return { avisos: decodificar(bruto), bruto }
}
