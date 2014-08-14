from django.conf.urls import patterns, include, url

from django.contrib import admin
from trade import views, cyboplus

admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'yjtrade.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^$', views.index),
    url(r'^initial_box', views.initial_box),
    url(r'^admin/', include(admin.site.urls)),
)

cyboplus.initialize()