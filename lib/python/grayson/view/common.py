import os
import json
import string
import traceback
import logging
import pwd

from django.conf import settings
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.template import RequestContext, loader
from grayson.common.util import GraysonUtil
from grayson.net.amqp import GraysonAMQPTransmitter

logger = logging.getLogger (__name__)

class DebugUser (object):
    username = "scox"

class GraysonWebConst:
    GRAYSON = "grayson"
    APP = "app"
    WORKFLOW = "workflow"
    TITLE = "title"
    USERNAME = "username"
    PASSWORD = "password"
    MESSAGE = "message"
    PATH = "path"
    MODEL_PATTERN = os.path.join ("models", "*.graphml")
    IO_READ = "r"
    IO_WRITE = "w"
    DAX_EXT = "%s.dax"
    UNPACK_EXT = "%s_upk"
    USER = "user"
    WORKFLOW_QUEUE = "workflow"
    MIME_HTML = "text/html"
    MIME_XML = "text/xml"
    MIME_TEXT = "text/plain"
    MIME_JSON = "application/json"

app_context = {
    GraysonWebConst.TITLE : GraysonWebConst.GRAYSON,
    'URL_PREFIX'          : settings.URL_PREFIX,
    'socketioListenPort'  : settings.SOCKET_IO_PORT 
    }

class ViewUtil:
    @staticmethod
    def form_workflow_path (user, file_name=""):
        return os.path.join (settings.GRAYSONWEB_WORKFLOW_ROOT,
                             user.username,
                             file_name)
    @staticmethod
    def publish (event):
        amqp = GraysonAMQPTransmitter (GraysonWebConst.WORKFLOW_QUEUE)
        text = json.dumps (event)
        amqp.send ([ text ])

    @staticmethod
    def get_user (request):
        user = None
        if settings.DEV:
            user = DebugUser ()
        else:
            try:
                user = request.session ['user']
            except:
                pass
        return user

    @staticmethod
    def get_os_username():
        return pwd.getpwuid( os.getuid() )[ 0 ]

    @staticmethod
    def get_app_username (request):
        username = ""
        user = ViewUtil.get_user (request)
        if user:
            username = user.username
        return username

    @staticmethod
    def get_response (template,
                      request,
                      context = {},
                      mimeType = GraysonWebConst.MIME_HTML,
                      status = 200):
        context [GraysonWebConst.APP] = app_context
        return HttpResponse (loader.
                             get_template ( template ).
                             render (RequestContext (request,
                                                     context)),
                             mimeType,
                             status,
                             mimeType)
    
    @staticmethod
    def get_text_response (text):
        return HttpResponse (text, GraysonWebConst.MIME_TEXT, 200, GraysonWebConst.MIME_TEXT)

    @staticmethod
    def get_json_response (response):
        text = ""
        if response:
            text = json.dumps (response, sort_keys=False, indent=2)
        return HttpResponse (text, GraysonWebConst.MIME_JSON, 200, GraysonWebConst.MIME_JSON)

    @staticmethod
    def setUser (username):
        app_context [GraysonWebConst.USERNAME] = username

class StrUtil(object):

    @staticmethod
    def afterlast (s, pat):
        value = None
        index = string.rfind (s, pat)
        if index > -1:
            value = s [index + len (pat):]
        return value

    @staticmethod
    def before (s, pat):
        value = None
        index = string.find (s, pat)
        if index > -1:
            value = s [:index + len (pat) - 1]
        return value

    @staticmethod
    def has (s, pat):
        return string.find (s, pat) > -1

    @staticmethod
    def between (s, s1, s2):
        value = None
        index = string.find (s, s1)
        if index > -1:
            rest = s [index + len (s1):]
            index2 = string.find (rest, s2)
            if index2 > -1:
                value = rest [ : index2]
        return value


class ViewController (object):

    def get_job_status (self, path):
        value = ''
        status = os.path.join (path, 'jobstate.log')
        try:
            text = GraysonUtil.readFile (status)
            text = text.split ('\n')
            if len (text) > 2:
                for line in text [ len (text) - 3 : ]:
                    logger.debug ('line: %s', line)
                    if 'DAGMAN_FINISHED' in line and '0 ***' in line:
                        value = '0'
                        break
                    elif 'DAGMAN_FINISHED' in line and '1 ***' in line:
                        value = '1'
                        break
        except IOError as e:
            pass
        return value

    def findFlows (self, request):
        user = ViewUtil.get_user (request)
        app_username = user.username
        os_username = ViewUtil.get_os_username ()

        logger.debug ("connect_flows:user: %s", user.username)
        workflowPath = ViewUtil.form_workflow_path (user)
        files = GraysonUtil.getDirs (of_dir=workflowPath)
        workdirs = GraysonUtil.findFilesByName (".*?\.grayson_upk$", files)
        response = []
        for workdir in workdirs:
            logger.debug ("connect_flows: workdir: %s", workdir) 
            conf = None
            try:
                conf = GraysonUtil.readJSONFile (os.path.join (workdir, "grayson.conf"))        
            except IOError as e:
                pass
            if conf:
                outputFile = conf ["output-file"]
                files = GraysonUtil.getFiles (workdir, recursive=False)
                runs = GraysonUtil.getDirs (os.path.join (workdir, "work", os_username, "pegasus", outputFile.replace (".dax", "")))
                runs.sort ()
                def normalize (line):
                    return GraysonUtil.getUserRelativePath (line, app_username)
                runDirs = GraysonUtil.findFilesByName ("[0-9]{8}T[0-9]{6}\-[0-9]{4}$", runs)
                item = {
                    "flow"   : normalize (workdir),
                    "id"     : outputFile,
                    "runs"   : map (lambda p : ' '.join ( [os.path.basename (p), self.get_job_status (p) ]), runDirs),
                    "graphs" : GraysonUtil.findFilesByName (".*?.graphml$", files),
                    "daxen"  : map (normalize, GraysonUtil.findFilesByName ("[a-zA-Z0-9\._\-]+\.dax$", files))
                    }
                response.append (item)
            response.sort (key = lambda k: k['id'])
        return response
