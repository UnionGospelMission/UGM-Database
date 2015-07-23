from UGM_Database import settings


def addBaseSite(request):
    return {'base_site': request.session.get('base_site', request.path.split('/')[1])}


def addBroadcastMessages(request):
    if getattr(settings, 'BROADCAST_MESSAGE', ''):
        return {'broadcast_message': settings.BROADCAST_MESSAGE}
    return {}
