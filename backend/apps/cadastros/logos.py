"""
Validação das logos enviadas na tela Parceiros.

O formato é conferido pelo conteúdo do arquivo, não pelo nome: um arquivo
qualquer renomeado para .png é recusado. SVG é texto (XML) e pode carregar
JavaScript; por isso recusamos qualquer SVG com script, eventos (onclick...),
links "javascript:" ou conteúdo HTML embutido.
"""

import xml.etree.ElementTree as ET

from django.core.exceptions import ValidationError

TAMANHO_MAXIMO = 2 * 1024 * 1024  # 2 MB
EXTENSOES = {'.png': 'png', '.jpg': 'jpg', '.jpeg': 'jpg', '.svg': 'svg'}

# Elementos de SVG que executam código ou embutem páginas HTML.
ELEMENTOS_PROIBIDOS = {'script', 'foreignobject', 'iframe', 'embed', 'object', 'handler', 'listener'}


def validar_logo(arquivo):
    """Confere tamanho e formato. Devolve a extensão certa ('.png', '.jpg' ou '.svg')."""
    if arquivo.size > TAMANHO_MAXIMO:
        raise ValidationError('A logo pode ter no máximo 2 MB.')
    nome = arquivo.name.lower()
    extensao = next((ext for ext in EXTENSOES if nome.endswith(ext)), None)
    if extensao is None:
        raise ValidationError('Envie a logo em PNG, JPG ou SVG.')

    conteudo = arquivo.read()
    arquivo.seek(0)  # volta ao início para o Django conseguir gravar o arquivo depois
    formato = EXTENSOES[extensao]
    if formato == 'png' and conteudo.startswith(b'\x89PNG\r\n\x1a\n'):
        return '.png'
    if formato == 'jpg' and conteudo.startswith(b'\xff\xd8\xff'):
        return '.jpg'
    if formato == 'svg':
        validar_svg(conteudo)
        return '.svg'
    raise ValidationError('O conteúdo do arquivo não é uma imagem PNG, JPG ou SVG válida.')


def validar_svg(conteudo):
    try:
        texto = conteudo.decode('utf-8-sig')
    except UnicodeDecodeError:
        raise ValidationError('O SVG enviado não é um arquivo de texto válido.')
    minusculo = texto.lower()
    # DOCTYPE/ENTITY permitem truques de XML (como expandir um texto até
    # travar o servidor). Logo de verdade não precisa disso.
    if '<!doctype' in minusculo or '<!entity' in minusculo:
        raise ValidationError('SVG com DOCTYPE não é aceito. Exporte a logo de novo como SVG simples.')
    if 'javascript:' in minusculo:
        raise ValidationError('SVG com código JavaScript não é aceito.')
    try:
        raiz = ET.fromstring(texto)
    except ET.ParseError:
        raise ValidationError('O SVG enviado está corrompido.')
    if nome_local(raiz.tag) != 'svg':
        raise ValidationError('O arquivo não é um SVG.')
    for elemento in raiz.iter():
        if nome_local(elemento.tag).lower() in ELEMENTOS_PROIBIDOS:
            raise ValidationError('SVG com script ou conteúdo embutido não é aceito.')
        if any(nome_local(atributo).lower().startswith('on') for atributo in elemento.attrib):
            raise ValidationError('SVG com código JavaScript não é aceito.')


def nome_local(tag):
    """'{http://www.w3.org/2000/svg}script' -> 'script' (tira o namespace do XML)."""
    return tag.rsplit('}', 1)[-1] if isinstance(tag, str) else ''
