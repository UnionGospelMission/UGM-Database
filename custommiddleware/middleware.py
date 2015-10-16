from django.contrib.sessions.models import Session
from django.contrib.auth.models import User

class setBaseSite():
    def process_request(self,request):
        print request.GET
        print request.POST
        print request.get_host()
        uid = Session.objects.get(pk=request.session.session_key).get_decoded().get('_auth_user_id')
        print User.objects.get(pk=uid)
        if request.path == '/':
            request.session['base_site']=''
        if not request.session.get('base_site',''):
            if 'guestmanagement' in request.path:
                request.session['base_site']='guestmanagement'
            elif 'purchaseorder' in request.path:
                request.session['base_site']='purchaseorder'
            elif 'truckmanagement' in request.path:
                request.session['base_site']='truckmanagement'

