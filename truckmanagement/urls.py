from django.conf.urls import url
from truckmanagement import views

urlpatterns = [
	url(r'^new/(?P<year>[0-9]+)/(?P<month>\S+)/(?P<day>[0-9]+)/$',views.new,name='new'),
	url(r'^donation/(?P<donation_id>[0-9]+)/$',views.donation,name='donation'),
	url(r'^schedule/$',views.schedule,name='schedule'),
	url(r'^logout/$',views.logout,name='logout'),
	url(r'^$', views.index, name='index'),
]
