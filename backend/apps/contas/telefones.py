"""Telefones brasileiros: normalização e links do WhatsApp."""

import re
from urllib.parse import quote


def somente_digitos(telefone):
    """'(11) 98765-4321' -> '11987654321'."""
    return re.sub(r'\D', '', telefone or '')


def formato_internacional(telefone):
    """
    Dígitos com o código do Brasil (55), ou '' se o número estiver incompleto.
    Telefones com DDD (10 ou 11 dígitos) ganham o 55 na frente.
    """
    digitos = somente_digitos(telefone)
    if len(digitos) in (10, 11):
        digitos = '55' + digitos
    return digitos if len(digitos) >= 12 else ''


def link_whatsapp(telefone, mensagem=''):
    """
    Link wa.me que abre uma conversa com esse número, com a mensagem pronta.
    Não usa nenhuma API paga: o link só abre o WhatsApp de quem clicou.
    """
    numero = formato_internacional(telefone)
    if not numero:
        return ''
    return f'https://wa.me/{numero}?text={quote(mensagem)}'


def mesmo_telefone(a, b):
    """Compara dois telefones ignorando formatação e o código 55."""
    return bool(formato_internacional(a)) and formato_internacional(a) == formato_internacional(b)
