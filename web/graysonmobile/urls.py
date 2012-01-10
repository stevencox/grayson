from django.conf.urls.defaults import *
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.contrib.auth.decorators import login_required

import web.graysonmobile.views

urlpatterns = patterns('',
    # Example:
    # (r'^web/', include('web.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    #(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    #(r'^admin/', include(admin.site.urls)),
    #(r'^admin/(.*)', admin.site.root),

    (r'^$',                    'web.graysonmobile.views.home'),
    (r'^about/$',              'web.graysonmobile.views.about'),
    (r'^flows/$',              'web.graysonmobile.views.flows'),
    (r'^runs/$',               'web.graysonmobile.views.runs'),
    #(r'/apple-touch-icon.png$','web.graysonmobile.views.icon'), # this has to be at the root.               
)



print "----------------------> %s " % staticfiles_urlpatterns ()
