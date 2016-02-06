from UGM_Database import settings


def addBaseSite(request):
    return {'base_site': request.session.get('base_site', request.path.split('/')[1])}


def addBroadcastMessages(request):
    if getattr(settings, 'BROADCAST_MESSAGE', ''):
        return {'broadcast_message': settings.BROADCAST_MESSAGE}
    if getattr(settings, 'ADMIN_BROADCAST_MESSAGE', '') and request.user.is_superuser:
        return {'admin_broadcast_message': settings.ADMIN_BROADCAST_MESSAGE}
    return {}
