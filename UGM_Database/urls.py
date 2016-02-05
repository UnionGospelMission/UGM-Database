from django.conf.urls import include, url
from django.contrib import admin
from django.http import HttpResponse
from UGM_Database import settings
from django.shortcuts import redirect
from django.contrib.staticfiles.urls import staticfiles_urlpatterns,static

def Print(value):
    print '\n\n\n\n',value

test = [i for i in settings.INSTALLED_APPS if i in ['guestmanagement','truckmanagement','purchaseorder']]


def index(request):
    sites = {'guestmanagement':'Guest Management',
             'truckmanagement':'Truck Management',
             'purchaseorder':'Purchase Orders',
    }
    if len(test)==1:
        return redirect('/%s/'%test[0])
    html = ' or '.join(["<a href='/%s/'>%s</a>"%(i,sites[i]) for i in test])
    return HttpResponse(html)

urlpatterns = [url(r'^%s/'%i, include('%s.urls'%i)) for i in test]

'''
urlpatterns = [
    # Examples:
    # url(r'^$', 'UGM_Database.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^truckmanagement/', include('truckmanagement.urls')),
    url(r'^report_builder/', include('report_builder.urls')),
    url(r'^guestmanagement/',include('guestmanagement.urls')),
]
'''

#urlpatterns += staticfiles_urlpatterns()
#urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns.append(url(r'^admin/', include(admin.site.urls)))
urlpatterns.append(url(r'^',index,name='index'))
