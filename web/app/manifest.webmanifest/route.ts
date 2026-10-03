import { manifesto } from '@/lib/manifesto'

// Manifesto do sistema (agenda). Cada barbearia tem também o seu, para a
// página de agendamento (app/agendar/[slug]/manifest.webmanifest).
export function GET() {
  return manifesto('Martinho', 'Martinho', '/')
}
