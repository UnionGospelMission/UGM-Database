from django.conf.urls import url,include
from purchaseorder import views

urlpatterns = [
		url(r'^$',views.index,name='index'),
		url(r'^logout/$',views.logout,name='logout'),
        url(r'^view/(?P<target>.+)/',views.view,name='view'),
		url(r'^view/',views.view,name='view'),
		url(r'^create/',views.new,name='view'),
]