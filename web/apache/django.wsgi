import os, sys, json

appRoot = os.path.dirname (os.path.dirname (os.path.dirname(os.path.realpath(__file__))))
for path in [ appRoot,
              os.path.join (appRoot, 'lib', 'python'),
              os.path.join (appRoot, 'web'),
              os.path.join (appRoot, 'web', 'graysonapp') ]:
    sys.path.append (path)

'''
sys.path.append('/opt/grayson')
sys.path.append('/opt/grayson/lib/python')
sys.path.append('/opt/grayson/web')
sys.path.append('/opt/grayson/web/graysonapp')
'''

#os.environ["CELERY_LOADER"] = "django"
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

import django.core.handlers.wsgi

_application = django.core.handlers.wsgi.WSGIHandler()


def application(environ, start_response):
    environ['PATH_INFO'] = environ['SCRIPT_NAME'] + environ['PATH_INFO']
    environ['SCRIPT_NAME'] = ''


    return _application(environ, start_response)


'''
   WSGIDaemonProcess engage-submit3.renci.org user=scox group=renci processes=2 threads=25
   WSGIProcessGroup engage-submit3.renci.org
   WSGISocketPrefix run/wsgi

   WSGIScriptAlias /grayson /opt/grayson/current/web/apache/django.wsgi

   Alias /grayson/static/ /opt/grayson/current/web/graysonapp/static/

   <Directory /opt/grayson/current/web/graysonapp/static/>
      Order deny,allow
      Allow from all
   </Directory>

   LogLevel info
'''