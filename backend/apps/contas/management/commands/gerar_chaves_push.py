"""
Gera o par de chaves VAPID usado para assinar as notificações push.

Rode uma vez e copie as duas linhas para o .env (desenvolvimento) e para as
variáveis de ambiente do Render (produção). Trocar as chaves depois invalida
todos os aparelhos inscritos: cada um precisa tocar em "Ativar avisos" de novo.
"""

import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.core.management.base import BaseCommand


def b64url(dados):
    return base64.urlsafe_b64encode(dados).rstrip(b'=').decode()


class Command(BaseCommand):
    help = 'Gera as chaves VAPID das notificações push.'

    def handle(self, *args, **opcoes):
        chave = ec.generate_private_key(ec.SECP256R1())
        privada = chave.private_numbers().private_value.to_bytes(32, 'big')
        publica = chave.public_key().public_bytes(
            serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
        )
        self.stdout.write('Copie para o .env e para o Render (Environment):\n')
        self.stdout.write(f'VAPID_PUBLIC_KEY={b64url(publica)}')
        self.stdout.write(f'VAPID_PRIVATE_KEY={b64url(privada)}')
        self.stdout.write('VAPID_EMAIL=mailto:seu-email@exemplo.com')
