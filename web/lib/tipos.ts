/**
 * Formato das linhas que o app lê do banco. Espelham as tabelas de
 * supabase/migrations/20261002000001_esquema.sql.
 *
 * (Dá para gerar estes tipos automaticamente com
 * `npx supabase gen types typescript`; enquanto o projeto é pequeno,
 * escritos à mão ficam mais legíveis.)
 */

export type Papel = 'dono' | 'barbeiro'
export type Status = 'agendado' | 'concluido' | 'cancelado' | 'faltou'

export const NOMES_STATUS: Record<Status, string> = {
  agendado: 'Agendado',
  concluido: 'Concluído',
  cancelado: 'Cancelado',
  faltou: 'Faltou',
}

export interface Barbearia {
  id: number
  nome: string
  slug: string
  telefone: string
  endereco: string
  agendamento_online: boolean
}

export interface Perfil {
  id: string
  barbearia_id: number | null
  nome: string
  papel: Papel
  superadmin: boolean
}

export interface Barbeiro {
  id: number
  barbearia_id: number
  nome: string
  telefone: string
  ativo: boolean
  usuario_id: string | null
}

export interface Servico {
  id: number
  nome: string
  preco: number
  duracao_minutos: number
  ativo: boolean
}

export interface Cliente {
  id: number
  nome: string
  telefone: string
  email: string
  data_nascimento: string | null
  endereco: string
  observacoes: string
}

export interface HorarioTrabalho {
  id: number
  barbeiro_id: number
  dia_semana: number
  inicio: string
  fim: string
}

export interface Ausencia {
  id: number
  barbeiro_id: number
  data_inicio: string
  data_fim: string
  hora_inicio: string | null
  hora_fim: string | null
  motivo: string
}

export interface Agendamento {
  id: number
  cliente_id: number
  barbeiro_id: number
  servico_id: number
  inicio: string
  fim: string
  status: Status
  observacoes: string
}
