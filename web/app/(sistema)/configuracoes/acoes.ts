'use server'

/**
 * Configurações da barbearia, só para o dono.
 *
 * Barbearia, serviços e barbeiros usam o cliente do usuário: a RLS só
 * deixa o dono gravar ("dono altera a barbearia", "dono cadastra
 * servicos"...). Logins usam o cliente admin (ver lib/logins.ts), sempre
 * com a barbearia da sessão.
 */
import { revalidatePath } from 'next/cache'
import { type EstadoFormulario, EMAIL_VALIDO, inteiro, marcado, texto, valores } from '@/lib/formularios'
import { criarLogin, SLUG_VALIDO } from '@/lib/logins'
import { exigirDono } from '@/lib/sessao'
import { clienteAdmin } from '@/lib/supabase/admin'

const pronto = (ok: string): EstadoFormulario => {
  revalidatePath('/configuracoes')
  return { ok }
}

export async function salvarBarbearia(_estado: EstadoFormulario, dados: FormData): Promise<EstadoFormulario> {
  const { supabase, barbearia } = await exigirDono()
  const v = valores(dados)
  const linha = {
    nome: texto(dados, 'nome'),
    slug: texto(dados, 'slug').toLowerCase(),
    telefone: texto(dados, 'telefone'),
    endereco: texto(dados, 'endereco'),
    agendamento_online: marcado(dados, 'agendamento_online'),
  }
  const erros: Record<string, string> = {}
  if (!linha.nome) erros.nome = 'Informe o nome.'
  if (!SLUG_VALIDO.test(linha.slug) || linha.slug.length > 60) erros.slug = 'Use só letras minúsculas, números e hífens, como "barbearia-do-joao".'
  if (Object.keys(erros).length) return { erros, valores: v }
  const { error } = await supabase.from('barbearias').update(linha).eq('id', barbearia.id)
  if (error?.code === '23505') return { erros: { slug: 'Este endereço já é usado por outra barbearia.' }, valores: v }
  if (error) return { erro: 'Não foi possível salvar.', valores: v }
  return pronto('Dados da barbearia salvos.')
}

export async function salvarServico(id: number | null, _estado: EstadoFormulario, dados: FormData): Promise<EstadoFormulario> {
  const { supabase, barbearia } = await exigirDono()
  const v = valores(dados)
  const preco = Number(texto(dados, 'preco').replace(',', '.'))
  const duracao = inteiro(dados, 'duracao_minutos')
  const linha = { nome: texto(dados, 'nome'), preco, duracao_minutos: duracao ?? 0, ativo: id ? marcado(dados, 'ativo') : true }
  const erros: Record<string, string> = {}
  if (!linha.nome) erros.nome = 'Informe o nome.'
  if (!Number.isFinite(preco) || preco < 0) erros.preco = 'Preço inválido.'
  if (!duracao || duracao < 5) erros.duracao_minutos = 'Mínimo de 5 minutos.'
  if (Object.keys(erros).length) return { erros, valores: v }
  const { error } = id
    ? await supabase.from('servicos').update(linha).eq('id', id)
    : await supabase.from('servicos').insert({ ...linha, barbearia_id: barbearia.id })
  if (error?.code === '23505') return { erros: { nome: 'Já existe um serviço com este nome.' }, valores: v }
  if (error) return { erro: 'Não foi possível salvar.', valores: v }
  return id ? pronto('Serviço salvo.') : { ...pronto('Serviço cadastrado.'), valores: {} }
}

export async function salvarBarbeiro(id: number | null, _estado: EstadoFormulario, dados: FormData): Promise<EstadoFormulario> {
  const { supabase, barbearia } = await exigirDono()
  const v = valores(dados)
  const linha = {
    nome: texto(dados, 'nome'),
    telefone: texto(dados, 'telefone'),
    ativo: id ? marcado(dados, 'ativo') : true,
    // Um login da mesma barbearia (a chave composta no banco garante).
    usuario_id: texto(dados, 'usuario_id') || null,
  }
  if (!linha.nome) return { erros: { nome: 'Informe o nome.' }, valores: v }
  const { error } = id
    ? await supabase.from('barbeiros').update(linha).eq('id', id)
    : await supabase.from('barbeiros').insert({ ...linha, barbearia_id: barbearia.id })
  if (error?.code === '23505') return { erros: { usuario_id: 'Este login já está ligado a outro barbeiro.' }, valores: v }
  if (error) return { erro: 'Não foi possível salvar.', valores: v }
  return id ? pronto('Barbeiro salvo.') : { ...pronto('Barbeiro cadastrado. Agora cadastre os horários dele em Horários.'), valores: {} }
}

export async function novoLogin(_estado: EstadoFormulario, dados: FormData): Promise<EstadoFormulario> {
  const { supabase, barbearia } = await exigirDono()
  const v = valores(dados)
  const email = texto(dados, 'email').toLowerCase()
  const senha = String(dados.get('senha') ?? '')
  const papel = texto(dados, 'papel') === 'dono' ? 'dono' : 'barbeiro'
  const barbeiro = inteiro(dados, 'barbeiro')
  const erros: Record<string, string> = {}
  if (!texto(dados, 'nome')) erros.nome = 'Informe o nome.'
  if (!EMAIL_VALIDO.test(email)) erros.email = 'Informe um e-mail válido.'
  if (senha.length < 8) erros.senha = 'A senha precisa ter pelo menos 8 caracteres.'
  if (Object.keys(erros).length) return { erros, valores: v }

  const criado = await criarLogin({ email, senha, nome: texto(dados, 'nome'), barbeariaId: barbearia.id, papel })
  if ('erro' in criado) return { erro: criado.erro, valores: v }
  if (barbeiro) await supabase.from('barbeiros').update({ usuario_id: criado.id }).eq('id', barbeiro)
  revalidatePath('/configuracoes')
  return { ok: `Login criado. Passe o e-mail e a senha para ${texto(dados, 'nome')}; dá para trocar a senha depois, em Minha senha.`, valores: {} }
}

export async function removerLogin(usuarioId: string) {
  const sessao = await exigirDono()
  if (usuarioId === sessao.usuarioId) return
  const admin = clienteAdmin()
  // Confere no banco que o login é desta barbearia antes de apagar.
  const { data: perfil } = await admin.from('perfis').select('barbearia_id').eq('id', usuarioId).maybeSingle()
  if (perfil?.barbearia_id !== sessao.barbearia.id) return
  // Apagar no Auth apaga o perfil (cascade) e desliga o barbeiro (set null).
  await admin.auth.admin.deleteUser(usuarioId)
  revalidatePath('/configuracoes')
}
