#!twistd -noy server.py

import sys
import os
import urllib
from twisted.application import internet, service
from twisted.web import server, resource, wsgi, static
from twisted.python import threadpool
from twisted.internet import reactor, protocol
from twisted.internet.ssl import DefaultOpenSSLContextFactory
from OpenSSL import SSL

import UGM_Database.settings as settings
import Root

PORT = settings.PORT
if not PORT:
    PORT = 8080

class OpenSSLContextFactory(DefaultOpenSSLContextFactory):
    def __init__(self, key, cert=None, chain=None,sslmethod=SSL.SSLv23_METHOD):
        self.key = key
        self.cert = cert
        self.chain = chain
        self.sslmethod = sslmethod
        self.cacheContext()
    
    def cacheContext(self):
        context = SSL.Context(self.sslmethod)
        if self.chain:
            context.use_certificate_chain_file(self.chain)
        else:
            context.use_certificate_file(self.cert)
        context.use_privatekey_file(self.key)
        self._context = context


class ThreadPoolService(service.Service):
    def __init__(self, pool):
        self.pool = pool

    def startService(self):
        service.Service.startService(self)
        self.pool.start()

    def stopService(self):
        service.Service.stopService(self)
        self.pool.stop()

def testVersion():
    settings.ADMIN_BROADCAST_MESSAGE=''
    remote_version = urllib.urlopen('https://raw.githubusercontent.com/lperkin1/UGM-Database/master/release').read()
    local_version = open('release','r').read()
    reactor.callLater(int(settings.MYSETTINGS['NEWVERSIONCHECK']),testVersion)
    if remote_version!=local_version:
        settings.ADMIN_BROADCAST_MESSAGE = "New Stable Version Available"
    else:
        remote_changelog = urllib.urlopen('https://raw.githubusercontent.com/lperkin1/UGM-Database/master/currentchanges').read()
        local_changelog = open('currentchanges','r').read()
        if remote_changelog!=local_changelog:
            settings.ADMIN_BROADCAST_MESSAGE += "New Unreleased Updates Available"

testVersion()

# Environment setup for your Django project files:
sys.path.insert(0, os.getcwd())
os.environ['DJANGO_SETTINGS_MODULE'] = 'UGM_Database.settings'
from django.core.handlers.wsgi import WSGIHandler

# Twisted Application Framework setup:
application = service.Application('twisted-django')


# WSGI container for Django, combine it with twisted.web.Resource:
# XXX this is the only 'ugly' part: see the 'getChild' method in twresource.Root 
# The MultiService allows to start Django and Twisted server as a daemon.

multi = service.MultiService()
pool = threadpool.ThreadPool()
tps = ThreadPoolService(pool)
tps.setServiceParent(multi)
import UGM_Database.wsgi

resource = Root.WSGIResource(reactor, tps.pool, UGM_Database.wsgi.application)
root = Root.Root(resource)


mediasrc = static.File(os.path.join(os.path.abspath("."), "static/media"))
staticsrc = static.File(os.path.join(os.path.abspath("."), "static"))
root.putChild("static", staticsrc)
root.putChild("media", mediasrc)




# The cool part! Add in pure Twisted Web Resouce in the mix
# This 'pure twisted' code could be using twisted's XMPP functionality, etc:


# Serve it up:
main_site = server.Site(root)
if settings.PRIVATE_KEY_FILE:
    print settings.PRIVATE_KEY_FILE
    internet.SSLServer(443, main_site, OpenSSLContextFactory(settings.PRIVATE_KEY_FILE, settings.PUBLIC_KEY_FILE, settings.CHAINED_CERTIFICATES_FILE)).setServiceParent(multi)
else:
    internet.TCPServer(PORT, main_site).setServiceParent(multi)
multi.setServiceParent(application)
