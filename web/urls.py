from django.conf.urls.defaults import *
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.contrib.auth.decorators import login_required

import web.graysonapp.views
import web.graysonmobile.views

# Uncomment the next two lines to enable the admin:
#from django.contrib import admin
#admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^web/', include('web.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    #(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    #(r'^admin/', include(admin.site.urls)),
    #(r'^admin/(.*)', admin.site.root),

    (r'^$',                     'web.graysonapp.views.home'),
    (r'^login/$',               'web.graysonapp.views.do_login'),
    (r'^logout/$',              'web.graysonapp.views.do_logout'),
    (r'^login_required/$',      'web.graysonapp.views.do_login_required'),
    (r'^conf/$',                'web.graysonapp.views.get_app_conf'),
    (r'^run/$',                 'web.graysonapp.views.run'),
    (r'^api_run/$',             'web.graysonapp.views.api_run'),
    (r'^get_workflow/$',        'web.graysonapp.views.get_workflow'),
    (r'^get_job_output/$',      'web.graysonapp.views.get_job_output'),
    (r'^connect_flows/$',       'web.graysonapp.views.connect_flows'),
    (r'^get_flow_events/$',     'web.graysonapp.views.get_flow_events'),
    (r'^get_flow_file/$',       'web.graysonapp.views.get_flow_file'),
    (r'^get_flow_status/$',     'web.graysonapp.views.get_flow_status'),
    (r'^get_compile_msgs/$',    'web.graysonapp.views.get_compile_msgs'),
    (r'^delete_run/$',          'web.graysonapp.views.delete_run'),
    (r'^grid_authenticate/$',   'web.graysonapp.views.grid_authenticate'),
    (r'^dirlist/$',             'web.graysonapp.views.dirlist'),
    (r'^getfile/$',             'web.graysonapp.views.getfile'),
    (r'^tests/$',               'web.graysonapp.views.tests'),
    (r'^mongo/$',               'web.graysonapp.views.mongo'),
    (r'^debugger/$',            'web.graysonapp.views.debugger'),

    (r'^mobile/', include('web.graysonmobile.urls')),
    (r'^apple-touch-icon.png$','web.graysonmobile.views.icon'),      # this has to be at the root.

    (r'^profile/password/$',         'django_ldapbackend.views.password_change'),
    (r'^profile/password/changed/$', 'django.contrib.auth.views.password_change_done'),

)

# ... the rest of your URLconf goes here ...

print "====static url patterns========================= \n%s" % staticfiles_urlpatterns()
#if len (staticfiles_urlpatterns()) == 0:
#    staticfiles_^static\/(?P<path>.*)$
urlpatterns += staticfiles_urlpatterns ()
 
print "----------------------> %s " % staticfiles_urlpatterns ()

import re
from django.conf import settings


def relocate_site(root, urlpatterns, relocate_settings=('LOGIN_URL',
                                                        'LOGOUT_URL',
                                                        'LOGIN_REDIRECT_URL',
                                                        'MEDIA_URL',
                                                        'ADMIN_MEDIA_PREFIX')):
    '''Relocate a site under a different mount point.
    
    Typically should be used in the top level ``urls.py``::
    
    from django.conf import settings
    from django.conf.urls.defaults import *
    
    urlpatterns = patterns('',
    ...
    )
    
    # define URL_PREFIX in settings.py
    relocate_site(settings.URL_PREFIX, urlpatterns)
    
    :param root: The sites mount point, e.g. /myapp/.
    :params urlpatterns: The top level url patterns list.
    :param relocate_settings: The setting variables with URL values to be also
    relocated. See also http://code.djangoproject.com/ticket/8906.
    '''
    root = root.strip('/')
    if root:
        for p in urlpatterns or ():
            p.regex = re.compile(r'^%s/%s' % (re.escape(root),
                                              p.regex.pattern.lstrip('^')))
        for name in relocate_settings or ():
            url = getattr(settings, name)
            if url.startswith('/'):
                setattr(settings, name, '/' + root + url)

relocate_site(settings.URL_PREFIX, urlpatterns)
    
