import type { Metadata } from 'next'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import { diaEMes, diaLocal, ddmm, horaLocal, maiuscula, nomeDoDia } from '@/lib/datas'
import { clienteDoUsuario } from '@/lib/supabase/servidor'
import { linkWhatsapp } from '@/lib/telefones'
import { CabecalhoPublico } from '@/components/CabecalhoPublico'

export const metadata: Metadata = { title: 'Agendado' }

/**
 * Página de confirmação. O endereço leva o código aleatório do
 * agendamento (uuid), e não o número: ninguém consegue ver o horário de
 * outra pessoa trocando o número na barra de endereço.
 */
export default async function Confirmado({ params }: PageProps<'/agendar/[slug]/confirmado/[codigo]'>) {
  const { slug, codigo } = await params
  if (!/^[0-9a-f-]{36}$/i.test(codigo)) notFound()
  const { data } = await (await clienteDoUsuario()).rpc('confirmacao_publica', { p_slug: slug, p_codigo: codigo })
  if (!data) notFound()
  const ag = data as {
    barbearia: { nome: string; telefone: string; endereco: string }
    inicio: string
    status: string
    servico: string
    barbeiro: string
    cliente: string
  }
  const dia = diaLocal(ag.inicio)
  const mensagem = `Olá! Sou ${ag.cliente} e agendei ${ag.servico.toLowerCase()} com ${ag.barbeiro} em ${ddmm(dia)} às ${horaLocal(ag.inicio)}.`
  const whatsapp = linkWhatsapp(ag.barbearia.telefone, mensagem)

  return (
    <>
      <CabecalhoPublico barbearia={ag.barbearia} />
      <main className="publico__conteudo publico__principal">
        <section className="passo confirmado">
          <span className="confirmado__marca" aria-hidden="true" />
          <h2 className="titulo">Horário confirmado</h2>
          <div className="resumo">
            <p>
              <strong>
                {maiuscula(nomeDoDia(dia))}, {diaEMes(dia)}
              </strong>{' '}
              às <strong>{horaLocal(ag.inicio)}</strong>
            </p>
            <p>
              {ag.servico} com {ag.barbeiro}
            </p>
            <p className="legenda">Em nome de {ag.cliente}</p>
          </div>
          {ag.status === 'cancelado' && <p className="erro-geral">Este agendamento foi cancelado pela barbearia.</p>}
          <p>Se precisar desmarcar ou mudar o horário, avise a barbearia.</p>
          <div className="linha-acoes">
            {whatsapp && (
              <a className="btn btn--primario" href={whatsapp} target="_blank" rel="noopener">
                Falar com a barbearia no WhatsApp
              </a>
            )}
            <Link className="btn btn--secundario" href={`/agendar/${slug}`}>
              Fazer outro agendamento
            </Link>
          </div>
        </section>
      </main>
    </>
  )
}
