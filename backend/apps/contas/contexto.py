from django.conf import settings


def push(request):
    """Deixa a chave pública das notificações disponível em todos os templates."""
    return {'VAPID_PUBLIC_KEY': settings.VAPID_PUBLIC_KEY}
