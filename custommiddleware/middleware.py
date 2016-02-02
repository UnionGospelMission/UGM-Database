from django.contrib.sessions.models import Session
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.shortcuts import redirect


def interactiveConsole(a,b=None):
    import code
    d = {}
    if b:
        d.update(b)
    d.update(a)
    c=code.InteractiveConsole(locals=d)
    c.interact()


class setBaseSite():
    def process_request(self,request):
        print request.GET
        print {k:v for k,v in request.POST.iteritems() if k!='password' and k!='csrfmiddlewaretoken'}
        print request.get_host()
        if request.session.session_key:
            uid = Session.objects.get(pk=request.session.session_key).get_decoded().get('_auth_user_id')
            if uid:
                user = User.objects.get(pk=uid)
                print user
                if request.path.startswith(reverse('admin:index')) and not user.is_superuser:
                    return redirect('/guestmanagement/')
                    
            else:
                print "Anonymous"
        else:
            print "Anonymous"
        if request.path == '/':
            request.session['base_site']=''
        if not request.session.get('base_site',''):
            if 'guestmanagement' in request.path:
                request.session['base_site']='guestmanagement'
            elif 'purchaseorder' in request.path:
                request.session['base_site']='purchaseorder'
            elif 'truckmanagement' in request.path:
                request.session['base_site']='truckmanagement'

