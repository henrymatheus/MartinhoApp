/**
 * Gera o par de chaves VAPID das notificações push.
 *
 * Só é preciso se você ainda não tem chaves. Se o Django já usava
 * VAPID_PUBLIC_KEY e VAPID_PRIVATE_KEY, reaproveite as mesmas: assim os
 * celulares já inscritos continuam recebendo os avisos depois da troca.
 *
 * Uso: npm run gerar-chaves-push
 */
import webpush from 'web-push'

const { publicKey, privateKey } = webpush.generateVAPIDKeys()
console.log('Copie para o .env.local e para as variáveis da Vercel:\n')
console.log(`NEXT_PUBLIC_VAPID_PUBLIC_KEY=${publicKey}`)
console.log(`VAPID_PRIVATE_KEY=${privateKey}`)
console.log('VAPID_EMAIL=mailto:seu-email@exemplo.com')
