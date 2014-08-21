from django.conf.urls import patterns, include, url

from django.contrib import admin
from trade import views, trader

admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'yjtrade.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^$', views.index),
    url(r'^initial_box', views.initial_box),
    url(r'^set_box', views.set_box),
    url(r'^start', views.start),
    url(r'^stop', views.stop),
    url(r'^status', views.status),
    url(r'^admin/', include(admin.site.urls)),
)
