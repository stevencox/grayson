import glob
import grp
import logging
import json
import os
import re
import shutil
import string
import traceback
import pwd

from django.conf import settings
from django.contrib.auth import authenticate, login
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.template import RequestContext, loader
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.csrf import csrf_exempt    
from django.utils.translation import ugettext as _
from django.contrib.auth import logout
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.decorators import login_required

from grayson.debug.grid import GridWorkflow
from grayson.executor import Executor
from grayson.myproxycontroller import MyProxyController
from grayson.common.util import GraysonUtil
from web.graysonapp.tasks import ExecuteWorkflow
from web.graysonapp.tasks import MonitorWorkflow
from web.graysonapp.tasks import WorkflowMonitor
from web.graysonapp.util import GraysonWebConst
from grayson.view.common import ViewUtil
from grayson.view.common import ViewController

@csrf_protect
def mobile (request, tests=False):
    context = {}
    return ViewUtil.get_response ("mobile/html/index.html", request, context)

#from web.graysonapp.models import Thing

logger = logging.getLogger (__name__)

@csrf_protect
def do_login (request):
    response = {
        "status"  : "fail",
        "message" : _("Failed to authenticate user")
        }
    username = request.POST [GraysonWebConst.USERNAME]
    password = request.POST [GraysonWebConst.PASSWORD]
    logging.info (_("processing authentication request for user[%s]"), username)
    try:
        user = authenticate (username = username, password = password)
        logger.debug ("graysonapp:do_login: ldap backedn returned user: %s is_active: %s", user, user.is_active)
        if user and user.is_active:
            login (request, user)
            logger.debug ("graysonapp:do_login: calling middleware login")
            request.session [GraysonWebConst.USER] = user
            response ["status"]   = "ok"
            response ["message"]  = _("authenticated")
            response ["clientId"] = user.username 
            ViewUtil.setUser (username)
    except Exception as e:
        traceback.print_exc ()
    return ViewUtil.get_json_response (response)

def do_logout (request):
    response = { "status" : "fail" }
    try:
        logout (request)
        response ["status"] = "ok"
    except Exception as e:
        traceback.print_exc ()
    return ViewUtil.get_json_response (response)

def do_login_required (request):
    return ViewUtil.get_json_response ({ "status" : "login_required" })

@csrf_protect
def home (request, tests=False):
    context = {
        "clientId"         : ViewUtil.get_app_username (request),
        "client_unit_test" : tests
        }
    return ViewUtil.get_response ("graysonapp/html/app.html", request, context)

def tests (request):
    return home (request, tests=True)

@login_required
def api_run (request):
    response = { "status" : "ok" }
    try:
        workflowId = None
        logger.debug ("request: %s", request.REQUEST)
        logger.debug ("files: %s", request.FILES)
        if GraysonWebConst.WORKFLOW in request.FILES:
            workflow = request.FILES [GraysonWebConst.WORKFLOW]
            logger.debug (_("Processing uploaded workfow archive: %s."), workflow)
            logger.debug ("Processing uploaded workfow archive: %s.", workflow)
            user = ViewUtil.get_user (request)
            file_name = ViewUtil.form_workflow_path (user, workflow.name)
            contentFile = ContentFile (workflow.read ())
            logger.debug ("saving filename: %s", file_name)
            archivePath = default_storage.save (file_name, contentFile)
            logger.debug ("""executing workflow - 
       user         : %s
       archive      : %s
       archivePath  : %s
       amqpSettings : %s
""", user, file_name, archivePath, settings.AMQP_SETTINGS)

            ExecuteWorkflow.delay (user         = user,
                                   archive      = file_name,
                                   archivePath  = archivePath,
                                   logRelPath   = settings.GRAYSONWEB_WORKFLOW_ROOT,
                                   amqpSettings = settings.AMQP_SETTINGS)
            logger.debug ("execute called..")
    except Exception as e:
        logger.error ("Exception occurred during api_run()")
        traceback.print_exc ()  
    logger.debug ("getting response object %s", response)
    return ViewUtil.get_json_response (response)

@login_required
def get_workflow (request):
    workflow = request.REQUEST ['workflow']   
    user = ViewUtil.get_user (request)
    workflowPath = ViewUtil.form_workflow_path (user, workflow)
    text = GraysonUtil.readFileAsString (workflowPath)
    return HttpResponse (text, GraysonWebConst.MIME_XML, 200, GraysonWebConst.MIME_XML)

@login_required
def get_job_output (request):
    user = ViewUtil.get_user (request)
    workdir = request.REQUEST ['workdir']
    workflow_id = request.REQUEST ['workflowid']
    job_id = request.REQUEST ['jobid']
    run_id = request.REQUEST ['runid']
    if not run_id:
        run_id = ""
    if not workflow_id:
        workflow_id = ""
    logger.debug ("getting job output: workdir=%s, workflowid: %s, runid: %s, jobid: %s", workdir, workflow_id, run_id, job_id)
    process_username = ViewUtil.get_os_username ()
    workdirPath = GraysonUtil.form_workdir_path (workdir, process_username, workflow_id, run_id)

    workdirPath = ViewUtil.form_workflow_path (user, workdirPath)

    logger.debug ("workdirPath: %s", workdirPath)

    text = ""

    if job_id.startswith ('/'):
        job_id = job_id [1:]
    concrete = os.path.join (workdirPath, job_id)
    logger.debug ('concrete: --- %s', concrete)
    if os.path.exists (concrete):
        logger.debug ("concrete --- : %s", concrete)
        text = GraysonUtil.readFile (concrete)
    else:
        logger.debug ("regex: --- : %s", concrete)
        workflow = GridWorkflow (workdirPath)
        outputs = workflow.getOutputFiles (subworkflows = [ workdirPath ], item = job_id) 
        jobOutput = None
        if outputs and len (outputs) > 0:
            jobOutput = outputs [0]
        logger.debug ("got job output: %s \n for job_id: %s", jobOutput, job_id)
        if jobOutput:
            text = GraysonUtil.readFileAsString (jobOutput)
    return ViewUtil.get_text_response (text)

@login_required
def get_flow_file (request):
    path = os.path.join (settings.GRAYSONWEB_WORKFLOW_ROOT, request.REQUEST ['path'])    
    text = GraysonUtil.readFileAsString (path) if os.path.exists (path) else ''
    return ViewUtil.get_text_response (text)
    
@login_required
def get_compile_msgs (request):
    log = request.REQUEST ['log']
    logger.debug ("getting compilation messages: log=%s", log)
    process_username = ViewUtil.get_os_username ()
    text = GraysonUtil.readFileAsString (log)
    text = unicode (text.replace ('\n', '<br/>')) if text else 'An unknown error occurred compiling the model.'
    return ViewUtil.get_text_response (text)

@login_required
def connect_flows (request):
    controller = ViewController ()
    response = controller.findFlows (request)
    return ViewUtil.get_json_response (response)

@login_required
def get_flow_events (request):
    workdir    = request.REQUEST ["workdir"]
    workflowId = request.REQUEST ["workflowid"]
    runId      = request.REQUEST ["runid"]    
    dax        = request.REQUEST ["dax"] if "dax" in request.REQUEST else None

    if not dax:
        dax = os.path.basename (workflowId)
        logger.debug ("dax: %s", dax)

    workflowName = os.path.basename (workflowId).replace (".dax", "")

    
    process_username = ViewUtil.get_os_username ()
    workdirPath = GraysonUtil.form_workdir_path (workdir, process_username, workflowName, runId)
    user = ViewUtil.get_user (request)
    workdirPath = ViewUtil.form_workflow_path (user, workdirPath)
    logger.debug ("launching monitor: user: %s, workdir: %s, workflowId: %s, runId: %s, dax: %s",
                  user.username, workdirPath, workflowId, runId, dax)
    monitor = WorkflowMonitor ()
    monitor.delay (username        = user.username, # route messages to a specific client 
                   workflowId      = workflowId,
                   workdir         = workdirPath,
                   dax             = dax,
                   logRelPath      = settings.GRAYSONWEB_WORKFLOW_ROOT,
                   amqpSettings    = settings.AMQP_SETTINGS,
                   eventBufferSize = settings.EVENT_BUFFER_SIZE)
    logger.debug ("launched workflow monitor")
    return ViewUtil.get_json_response ({ "status" : "ok" })

@login_required
def delete_run (request):
    response = { "status" : "ok" }
    workdir = request.REQUEST ["workdir"]
    workflowId = request.REQUEST ["workflowid"]
    runId = request.REQUEST ["runid"]    
    workflowName = os.path.basename (workflowId).replace (".dax", "")
    process_username = ViewUtil.get_os_username ()    
    workdirPath = workdir
    if runId:
        workdirPath = GraysonUtil.form_workdir_path (workdir, process_username, workflowName, runId)
    user = ViewUtil.get_user (request)
    workdirPath = ViewUtil.form_workflow_path (user, workdirPath)
    logger.debug ("DELETING workflow run: %s", workdirPath)
    try:
        shutil.rmtree (workdirPath)
    except Exception as e:
        logger.exception ("exception deleting %s", workdirPath)
        traceback.print_exc ()
        response ["status"] = "fail"
    return ViewUtil.get_json_response (response)
    
@login_required
def put_file (request):
    path = request.REQUEST ["path"]
    content = request.REQUEST ["content"]
    logger.debug ("writing file: %s", path)
    GraysonUtil.writeFile (path, content)
    return ViewUtil.get_json_response ({ "status" : "ok" })
    
@login_required
def get_app_conf (request):
    return ViewUtil.get_response (template = 'conf.js',
                                        request  = request,
                                        context  = {},
                                        mimeType = 'text/application-javascript')
                         
@login_required
def get_flow_status (request):
    path = os.path.join (settings.GRAYSONWEB_WORKFLOW_ROOT,
                         request.REQUEST ['path'])
    output = []
    executor = Executor ({ 'flowPath' : path })
    pegasus = os.environ ['PEGASUS_HOME']
    executor.execute (command   = "%s/bin/pegasus-status -l ${flowPath}" % pegasus,
                      pipe      = True,
                      processor = lambda n : output.append (n))
    return ViewUtil.get_text_response (''.join (output))

@login_required
def grid_authenticate (request):
    result = { 'status' : 'ok' }
    try:
        myproxyController = MyProxyController (
            port = settings.MYPROXY_PORT,
            hostname = settings.MYPROXY_HOST,
            serverDN = settings.MYPROXY_SERVER_DN,
            proxyCertMaxLifetime = settings.MYPROXY_CERT_MAX_LIFETIME,
            proxyCertLifetime = settings.MYPROXY_CERT_LIFETIME)

        myproxyController.login (username = request.REQUEST ['username'],
                                 password = request.REQUEST ['password'],
                                 certPath = settings.MYPROXY_CERTPATH,
                                 vdtLocation = settings.VDT_LOCATION)
    except Exception as ex:
        text = "error getting credential from myproxy: %s" % ex
        logger.error (text)
        result ['status'] = 'error'
        result ['message'] = text
        traceback.print_exc (ex)
    return ViewUtil.get_json_response (result)

@login_required
@csrf_exempt
def dirlist(request):
    r=['<ul class="jqueryFileTree" style="display: none;">']
    try:
        r=['<ul class="jqueryFileTree" style="display: none;">']
        
        d = request.REQUEST ['dir']
        d = os.path.join (settings.GRAYSONWEB_WORKFLOW_ROOT, d)
        files = os.listdir(d)                                                                                                                                                                        
        files.sort ()                                                                                                                                                                                
        for f in files:
            ff=os.path.join(d,f)
            if os.path.isdir(ff):
                r.append('<li class="directory collapsed"><a id="ft_%s" href="#" rel="%s/">%s</a></li>' % (f.replace ('-', '_').replace ('.', '_'), ff,f))
            else:
                e=os.path.splitext(f)[1][1:] # get .ext and remove dot
                r.append('<li class="file ext_%s"><a id="ft_%s" href="#" rel="%s">%s</a></li>' % (f.replace ('-', '_').replace ('.', '_'), e,ff,f))
        r.append('</ul>')
    except Exception,e:
        r.append('Unable to read directory: %s' % str(e))
    r.append('</ul>')
    return HttpResponse(''.join(r))

@login_required
def getfile (request):
    # TODO: construct path dynamically and selectively for security purposes.
    return ViewUtil.get_text_response (GraysonUtil.readFile (request.REQUEST ['file']))

@csrf_protect
def mobile (request, tests=False):
    context = {}
    return ViewUtil.get_response ("mobile/html/index.html", request, context)

'''
def mongo (request):
    for k in request.REQUEST.iterkeys ():
        print "key: %s" % k
    op = request.REQUEST ["operator"]
    args = request.REQUEST ["args"]
    if args:
        args = args.split (',')
        t = Thing (title = args[0], text = args[1])
        t.save ()
    return ViewUtil.get_text_response ('')
'''
