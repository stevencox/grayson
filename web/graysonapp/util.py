from django.conf import settings
from grayson.net.amqp import GraysonAMQPTransmitter

import os
import json
import string
import traceback

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

class Workflow(object):
    def __init__(self, client, workflowId, workdir, workflow_src):
        self.client = client
        self.workflowId = workflowId
        self.workdir = workdir
        self.workflow_src = workflow_src

class GraysonWebUtil:
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
            


# http://djangosnippets.org/snippets/80/
# Author: limodou@gmail.com
# version: 0.1
# Url filter middleware
# Update:
#   0.1
'''
from django.conf import settings
from utils.common import get_func
import re

class FilterMiddleware(object):
    def process_request(self, request):
        filter_items = getattr(settings, 'FILTERS', ())
        for v in filter_items:
            r, func = v
            if not isinstance(r, (list, tuple)):
                r = [r]
            for p in r:
                if isinstance(p, (str, unicode)):
                    p = re.compile(p)
                m = p.match(request.path[1:])
                if m:
                    kwargs = m.groupdict()
                    if kwargs:
                        args = ()
                    else:
                        args = m.groups()
                    return get_func(func)(request, *args, **kwargs)
                    '''
