'use server'

/**
 * Painel do superadmin (você): criar barbearias com o login do dono e
 * gerar links para definir senha. Usa o cliente admin, que ignora a RLS,
 * por isso toda ação começa conferindo exigirSuperadmin().
 */
import { revalidatePath } from 'next/cache'
import { type EstadoFormulario, EMAIL_VALIDO, texto, valores } from '@/lib/formularios'
import { criarLogin, gerarSlug, linkParaDefinirSenha, SLUG_VALIDO } from '@/lib/logins'
import { exigirSuperadmin } from '@/lib/sessao'
import { clienteAdmin } from '@/lib/supabase/admin'

export async function novaBarbearia(_estado: EstadoFormulario, dados: FormData): Promise<EstadoFormulario> {
  await exigirSuperadmin()
  const v = valores(dados)
  const nome = texto(dados, 'nome')
  const slug = (texto(dados, 'slug') || gerarSlug(nome)).toLowerCase()
  const email = texto(dados, 'email').toLowerCase()
  const senha = String(dados.get('senha') ?? '')
  const erros: Record<string, string> = {}
  if (!nome) erros.nome = 'Informe o nome.'
  if (!SLUG_VALIDO.test(slug)) erros.slug = 'Use só letras minúsculas, números e hífens.'
  if (!texto(dados, 'dono')) erros.dono = 'Informe o nome do dono.'
  if (!EMAIL_VALIDO.test(email)) erros.email = 'Informe um e-mail válido.'
  if (senha.length < 8) erros.senha = 'Pelo menos 8 caracteres.'
  if (Object.keys(erros).length) return { erros, valores: v }

  const admin = clienteAdmin()
  const { data: barbearia, error } = await admin
    .from('barbearias')
    .insert({ nome, slug, telefone: texto(dados, 'telefone') })
    .select('id')
    .single()
  if (error?.code === '23505') return { erros: { slug: 'Este endereço já é usado por outra barbearia.' }, valores: v }
  if (error || !barbearia) return { erro: 'Não foi possível criar a barbearia.', valores: v }

  const login = await criarLogin({ email, senha, nome: texto(dados, 'dono'), barbeariaId: barbearia.id, papel: 'dono' })
  if ('erro' in login) {
    await admin.from('barbearias').delete().eq('id', barbearia.id)
    return { erro: login.erro, valores: v }
  }
  revalidatePath('/admin')
  return { ok: `Barbearia criada. Página de agendamento: /agendar/${slug}`, valores: {} }
}

export async function gerarLinkDeSenha(_estado: EstadoFormulario, dados: FormData): Promise<EstadoFormulario> {
  await exigirSuperadmin()
  const email = texto(dados, 'email')
  const link = await linkParaDefinirSenha(email)
  if (!link) return { erro: 'Não foi possível gerar o link.' }
  return { ok: `Envie este link para ${email} (vale uma vez):`, extra: { link } }
}
