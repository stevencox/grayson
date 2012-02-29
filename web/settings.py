# Django settings for web project.

import os
import sys
import json

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))

nodeConf = json.loads (open ( os.path.join ( os.path.dirname (SITE_ROOT), "conf", "grayson.conf" )).read ())
WORKFLOW_QUEUE_NAME = nodeConf ["queueSettings"]["QName"]
URL_PREFIX = nodeConf ["urlPrefix"]
BROKER_PORT = nodeConf["amqpSettings"]["port"]
SOCKET_IO_PORT = nodeConf ["socketioListenPort"]
DATA_ROOT = os.path.join (SITE_ROOT, os.path.sep.join (nodeConf ["var"]))

DEBUG = True #False #nodeConf ["debug"]
DEV = DEBUG #False #True
TEMPLATE_DEBUG = DEBUG

EVENT_BUFFER_SIZE = 10

LOGIN_URL="/login_required/"

sys.path.insert(0, os.path.join (SITE_ROOT, "..", "lib", "python"))

#DATA_ROOT = os.path.join (SITE_ROOT, "..", "var")
LOG_ROOT = os.path.join (DATA_ROOT, "logs")
STATIC_URL = os.path.join (URL_PREFIX, 'static/') #'http://localhost/static/' 
STATIC_ROOT = os.path.join (SITE_ROOT, 'static')

MONGO = False #DEV

if MONGO:
    SESSION_ENGINE = 'mongoengine.django.sessions'
    DATABASES = {
        'default': {
            'ENGINE': '', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
            'NAME': os.path.join(DATA_ROOT, 'database.db'),  # Or path to database file if using sqlite3.
            'USER': '',                      # Not used with sqlite3.
            'PASSWORD': '',                  # Not used with sqlite3.
            'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
            'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
            }
        }

    from mongoengine import connect
    connect('test')
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
            'NAME': os.path.join(DATA_ROOT, 'database.db'),  # Or path to database file if using sqlite3.
            'USER': '',                      # Not used with sqlite3.
            'PASSWORD': '',                  # Not used with sqlite3.
            'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
            'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
            }
        }

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = DATA_ROOT

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'i=+1v#mrayy5++d-ssho7ihdd)*5k=^fd3-ulegpjg9(+2#m8i'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
#    'django.middleware.gzip.GZipMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'web.urls'

TEMPLATE_DIRS = (

    "/".join ([ SITE_ROOT, 'graysonapp', 'html' ]),
    "/".join ([ SITE_ROOT ]),
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

'''
compress
'''
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    # other finders..
    'compressor.finders.CompressorFinder',
)
#COMPRESS_ENABLED = True


INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'compressor',
    'web.graysonapp',
    'web.graysonmobile',
    # Uncomment the next line to enable the admin:
    #'django.contrib.admin',

    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
)
''' admin
TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.messages.context_processors.messages',
    'django.contrib.auth.context_processors.auth',
)
'''
INSTALLED_APPS += ("djcelery", )
import djcelery
#CELERY_DISABLE_RATE_LIMITS = False
#CELERY_ALWAYS_EAGER = True
#BROKER_PORT = 40966
djcelery.setup_loader()

if MONGO:
    AUTHENTICATION_BACKENDS = (
        'mongoengine.django.auth.MongoEngineBackend',
        )
else:
    AUTHENTICATION_BACKENDS = (
        'web.graysonapp.LDAPAuthBackend.RENCILDAPBackend',
        )


RENCI_LDAP_URI='ldaps://ldap.renci.org'
RENCI_LDAP_BASE='dc=renci,dc=org'
RENCI_LDAP_USER_BASE='uid=%s,ou=fte,ou=people,dc=renci,dc=org'

GRAYSONWEB_WORKFLOW_ROOT=os.path.join(DATA_ROOT, 'workflows')

VDT_LOCATION = '/opt/osg/1.2.18/osg-1.2.18'
MYPROXY_PORT = 7512
MYPROXY_HOST = 'engage-central.renci.org'
MYPROXY_SERVER_DN = '/DC=org/DC=doegrids/OU=Services/CN=engage-central.renci.org'
MYPROXY_CERT_MAX_LIFETIME = 80000
MYPROXY_CERT_LIFETIME = 70000
MYPROXY_CERTPATH = os.path.join (DATA_ROOT, 'proxy')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'filters': {
    },
    'handlers': {
        'null': {
            'level':'DEBUG',
            'class':'django.utils.log.NullHandler',
        },
        'console':{
            'level':'DEBUG',
            'class':'logging.StreamHandler',
            'formatter': 'simple'
        },
        'fileHandler': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter' : 'simple',
            'filename' : os.path.join (LOG_ROOT, 'grayson.log'),
            'maxBytes' : '1024',
            'backupCount' : '3'
        }
    },
    'loggers': {

        # ===================================
        # ==      W E B                    ==
        # ===================================
        'django': {
            'handlers':['null', 'fileHandler', 'console' ],
            'propagate': True,
            'level':'ERROR',
        },
        'django.request': {
            'handlers': ['fileHandler'],
            'level': 'ERROR',
            'propagate': False,
        },
        'web.graysonapp.views': {
            'handlers': ['console', 'fileHandler'],
            'level': 'DEBUG'
        },
        'web.graysonapp.models.GraysonTestCase': {
            'handlers': ['console', 'fileHandler'],
            'level': 'ERROR'
        },
        'web.graysonapp.LDAPAuthBackend': {
            'handlers': ['console', 'fileHandler'],
            'level': 'DEBUG'
        },
        'grayson.myproxycontroller': {
            'handlers': ['console', 'fileHandler'],
            'level': 'INFO'
        },

        # ===================================
        # ==        C O M M O N            ==
        # ===================================
        'grayson.util' : {
            'handlers' : [ 'console', 'fileHandler' ],
            'level'    : 'ERROR'
        },

        # ===================================
        # ==        C O M P I L E R        ==
        # ===================================
        'grayson.compiler.compiler' : {
            'handlers' : [ 'console', 'fileHandler' ],
            'level'    : 'INFO'
        },

        # ===================================
        # ==        D E B U G G E R        ==
        # ===================================
        'grayson.net.amqp' : {
            'handlers' : [ 'console', 'fileHandler' ],
            'level'    : 'ERROR'
        },
        'grayson.debug.event' : {
            'handlers' : [ 'console', 'fileHandler' ],
            'level'    : 'DEBUG'
        },
        'grayson.debug.grid' : {
            'handlers' : [ 'console', 'fileHandler' ],
            'level'    : 'DEBUG'
        }

    }
}

