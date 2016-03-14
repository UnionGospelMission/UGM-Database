from twisted.web import server, resource, client
from twisted.web.util import Redirect
from twisted.internet import defer
from twisted.python.filepath import FilePath
from twisted.web import wsgi
from twisted.web.wsgi import _WSGIResponse, NOT_DONE_YET
filepath = FilePath('static')


class WSGIResource(wsgi.WSGIResource):
    def render(self, request):
        """
        Turn the request into the appropriate C{environ} C{dict} suitable to be
        passed to the WSGI application object and then pass it on.

        The WSGI application object is given almost complete control of the
        rendering process.  C{NOT_DONE_YET} will always be returned in order
        and response completion will be dictated by the application object, as
        will the status, headers, and the response body.
        """
        response = _WSGIResponse(
            self._reactor, self._threadpool, self._application, request)
        response.environ['IRequest']=request
        response.start()
        return NOT_DONE_YET


class staticList(resource.Resource):
    def append(self, value):
        self.children.append(value)
    def __init__(self):
        self.children=[]
    def getChild(self, path, request):
        if 'dynamicforms' in request.postpath or 'staticforms' in request.postpath or 'guestpictures' in request.postpath:
            from django.contrib.auth.models import User
            from datetime import datetime
            from django.contrib.sessions.models import Session
            from guestmanagement.views import testPermission
            headers=request.received_headers
            cookies={i.split('=')[0].strip():i.split('=')[1].strip() for i in headers['cookie'].split(';')}
            session_id = cookies.get('sessionid',None)
            if not session_id:
                return Redirect('/guestmanagement/')
            sessions=Session.objects.filter(session_key=session_id, expire_date__gte=datetime.now())
            user = None
            session = {}
            if sessions:
                session=sessions[0].get_decoded()
                users = User.objects.filter(id=session.get('_auth_user_id', None))
                if users:
                    user = users[0]
            try:
                if not testPermission(request.path,user,session,testurl=True):
                    return Redirect('/guestmanagement/')
            except Exception, e:
                from django.core import mail
                import traceback,sys
                exc = sys.exc_info()
                subject = e.message.replace('\n', '\\n').replace('\r', '\\r')[:989]
                message = "%s\n\nglobals=%s\n\nlocals=%s" % ('\n'.join(traceback.format_exception(*exc)),str(globals()),str(locals()))
                mail.mail_admins(subject, message, fail_silently=True)
                return Redirect('/guestmanagement/')
        r=None
        for child in self.children:
            r=child.getChild(path,request)
            if not isinstance(r,resource.NoResource):
                return r
        return r




class Root(resource.Resource):
    def __init__(self, wsgi_resource):
        self.staticpages=staticList()
        resource.Resource.__init__(self)
        self.wsgi_resource = wsgi_resource
        resource.Resource.putChild(self, 'static', self.staticpages)
    def getChild(self, path, request):
        path0 = request.prepath.pop(0)
        request.postpath.insert(0, path0)
        return self.wsgi_resource
    def putChild(self, path, rsrc):
        if path.startswith('static'):
            self.staticpages.append(rsrc)
        else:
            resource.Resource.putChild(self, path, rsrc)
