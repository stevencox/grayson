import ldap
import logging

from django.conf import settings
from django.contrib.auth.models import User

logger = logging.getLogger (__name__)

class RENCILDAPBackend:

    supports_object_permissions = False
    supports_anonymous_user = False

    def __init__(self):
        self.uri = settings.RENCI_LDAP_URI
        self.base = settings.RENCI_LDAP_BASE
        self.ldap_connection = ldap.initialize (self.uri)                                                

    def authenticate_user (self, username, password):
        qualified_name = settings.RENCI_LDAP_USER_BASE % username
        logger.debug ("ldap:simple_bind_s: qualified_name: %s", qualified_name)
        result = self.ldap_connection.simple_bind_s (qualified_name, password)
        logger.debug ("result: %s", result)
        return result

    def authenticate (self, username=None, password=None):
        result = None
        if settings.DEV:
            result = User.objects.get (username=username)
        else:
            try:
                logger.debug ("authenticating user %s via ldap.", username)
                authentication_result = self.authenticate_user (username, password)
                if authentication_result:
                    try:
                        logger.debug ("ldap:authenticate: authenticate returned object. Looking up user %s", username)
                        user = User.objects.get (username = username)
                        result = user
                        logger.debug ("ldap:authenticate: got user object: %s", user)
                        result = user
                    except User.DoesNotExist:
                        logger.debug ("ldap:authenticate: got exception")
                        # Create a new user. Note that we can set password
                        # to anything, because it won't be checked; the password
                        # from settings.py will.
                        '''
                        user = User(username=username, password='get from settings.py')
                        user.is_staff = True
                        user.is_superuser = True
                        user.save ()
                        '''
                        pass
                else:
                    logger.debug ("ldap:authenticate_user: returned null object")
            except ldap.INVALID_CREDENTIALS:
                logger.error ("ldap exception: invalid credential exception for user: %s", username)
            except ldap.UNWILLING_TO_PERFORM:
                logger.error ("ldap exception: unwilling to perform bind with empty password for user: %s", username)
            except:
                logger.error ("ldap exception: unknown authentication failure for user: %s", username)
        return result

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
