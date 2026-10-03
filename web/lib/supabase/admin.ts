import 'server-only'
import { createClient } from '@supabase/supabase-js'
import { variavel } from '../ambiente'

/**
 * Cliente com a chave secreta (service role): IGNORA a RLS.
 *
 * Só é usado no servidor, em três situações em que não há um usuário da
 * barbearia por trás da operação, ou em que é preciso mexer no Supabase
 * Auth (criar logins):
 *   1. painel do superadmin (criar barbearias e logins);
 *   2. dono criando o login de um barbeiro (Configurações);
 *   3. envio das notificações push (ler os aparelhos dos destinatários).
 *
 * `import 'server-only'` faz o build falhar se este arquivo for importado
 * por um componente do navegador, então a chave nunca vaza.
 */
export function clienteAdmin() {
  return createClient(variavel('NEXT_PUBLIC_SUPABASE_URL'), variavel('SUPABASE_SECRET_KEY'), {
    auth: { persistSession: false, autoRefreshToken: false },
  })
}
