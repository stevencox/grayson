import logging
import os

from util import GraysonUtil
from myproxy.client import CaseSensitiveConfigParser
from myproxy.client import MyProxyClientGetError
from myproxy.client import MyProxyClient
from string import Template

logger = logging.getLogger (__name__)

class MyProxyController (object):

    def __init__(self, port, hostname, serverDN, proxyCertMaxLifetime=None, proxyCertLifetime=None):
        self._client = MyProxyClient ()
        self._client.port = port
        self._client.hostname = hostname
        self._client.serverDN = serverDN
        if proxyCertMaxLifetime:
            self._client.proxyCertMaxLifetime = proxyCertMaxLifetime
        if proxyCertLifetime:
            self._client.proxyCertLifetime = proxyCertLifetime

    def login (self, username, password, certPath, vdtLocation=None):
        proxyFileName = self.formProxyFileName (username, certPath)
        if not username or len (username) == 0:
            raise ValueError ("invalid username")
        if not password or len (password) == 0:
            raise ValueError ("invalid username")
        else:
            logger.info ('myproxy logon with username: %s', username)
            if vdtLocation:
                context = {
                    'username'      : username,
                    'serverDN'      : self._client.serverDN,
                    'hostname' 	    : self._client.hostname,
                    'password'      : password,
                    'proxyFileName' : proxyFileName,
                    'certPath'      : certPath,
                    'vdtLocation'   : vdtLocation
                    }

                command = """
                . ${vdtLocation}/setup.sh  &&                                         \
                echo ${password} |                                                    \
                MYPROXY_SERVER_DN='${serverDN}'                                       \
                myproxy-get-delegation                                                \
                   --pshost ${hostname}                                               \
                   --username ${username}                                             \
                   --stdin_pass                                                       \
                   --out ${proxyFileName} >> ${certPath}/../logs/myproxy.log 2>&1 """
                os.system (Template (command).substitute (context))
            else:
                proxy = self._client.logon (username = username, passphrase = password)
                
                logger.info ("writing proxy certificate retrieved from myproxy for user [%s] at [%s]", username, certPath)
                if not os.path.exists (certPath):
                    os.makedirs (certPath)
                GraysonUtil.writeFile (outputPath = proxyFileName, data = proxy [0])

    def formProxyFileName (self, username, certPath):
        return os.path.join (certPath, "x509_proxy_%s" % username)
