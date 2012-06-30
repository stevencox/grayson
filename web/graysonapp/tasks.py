import glob
import logging
import json
import os
import re
import shutil
import string
import sys
import time
import traceback
from celery.decorators import task
from celery.task import Task
from django.conf import settings
from django.utils.translation import ugettext as _
from django.core.cache import cache
from django.utils.hashcompat import md5_constructor as md5
from grayson.net.amqp import GraysonAMQPTransmitter
from grayson.pegasus import WorkflowParser
from grayson.executor import Executor
from grayson.compiler.compiler import GraysonCompiler
from grayson.compiler.compiler import CompilerPlugin
from grayson.packager import GraysonPackager
from grayson.net.amqp import GraysonAMQPTransmitter
from grayson.debug.monitor import WorkflowMonitorCompilerPlugin
from grayson.debug.grid import WorkflowMonitorTask
from grayson.debug.event import EventStream
from web.graysonapp.util import GraysonWebConst
from web.graysonapp.util import GraysonWebUtil
from celery.task.control import inspect

logger = logging.getLogger (__name__)

class WorkflowMonitor (Task):

    name = "workflow.monitor"

    '''
    Load balance event tasks (consumers of requests for events; producers of events) here.
       - http://docs.celeryproject.org/en/latest/userguide/workers.html#inspecting-workers
          {
              'scox.europa.renci.org':  [
                  { u'args' : u'[]', 
                    u'time_start': 1340891522.549662, 
                    u'name': u'web.graysonapp.tasks.ExecuteWorkflow', 
                    u'delivery_info': {
                        u'routing_key': u'celery', 
                        u'exchange': u'celery'}, 
                        u'hostname': u'scox.europa.renci.org',
                        u'acknowledged': True, 
                        u'kwargs': u"{
                            'archivePath': u'/home/scox/dev/grayson/web/../var/workflows/scox/test-context_30.grayson', 
                            'workflowRoot': u'/home/scox/dev/grayson/web/../var/workflows', 
                            'user': <grayson.view.common.DebugUser object at 0x2a10fd0>, 
                            'amqpSettings': <grayson.net.amqp.AMQPSettings object at 0x2a1f090>, 
                            'archive': u'/home/scox/dev/grayson/web/../var/workflows/scox/test-context.grayson'
                        }", 
                        u'id': u'32070c51-36a5-4c4f-b7bb-3014aedd948a', 
                        u'worker_pid': 8831
                  }
              ]
          }

          >>> from celery.task.control import revoke
          >>> revoke("d9078da5-9915-40a0-bfa1-392c7bde42ed")
          '''
    @staticmethod
    def ensureRunning (workflowRoot=".", amqpSettings=None, eventBufferSize=0):
        running = False
        tasks = inspect ()
        active = tasks.active ()
        logger.debug ("%s" % active)
        logger.debug ("%s", json.dumps (active, indent=3, sort_keys=True))
        for atHost in active:
            activeAt = active [atHost]
            for task in activeAt:
                name = task ['name']
                logger.debug ("task name: %s", name)
                if WorkflowMonitor.name == name:
                    logger.debug ("WorkflowMonitor task invoked")
                    running = True
                    break
            if running:
                break
        if not running:
            monitor = WorkflowMonitor ()
            WorkflowMonitor.delay (workflowRoot, amqpSettings, eventBufferSize)

    def run (self, workflowRoot=".", amqpSettings=None, eventBufferSize=0, **kwargs):
        logger = self.get_logger (**kwargs)
        logger.debug ("WorkflowMonitor task is being started.")
        monitor = WorkflowMonitorTask (workflowRoot, amqpSettings, eventBufferSize)
        monitor.execute ()

@task()
def ExecuteWorkflow (user, archive, archivePath, workflowRoot=".", amqpSettings=None):
    logger.info ("executeworkflow:amqpsettings: %s", amqpSettings)
    try:
        basename = os.path.basename (archive)
        unpack_dir = GraysonWebUtil.form_workflow_path (user, GraysonWebConst.UNPACK_EXT % basename)

        # If we don't open up permissions, using x509userproxy doesn't work. i.e. users can't run as themselves and write files here, for example.
        chmodCommand = "chmod -R 777 %s" % unpack_dir
        logger.debug ("setting output directory permissions: %s" % chmodCommand)
        os.system (chmodCommand)
        
        log_file = os.path.join (unpack_dir, "log.txt")
        executionMonitor = WorkflowMonitorCompilerPlugin (user.username,
                                                          unpack_dir,
                                                          workflowRoot,
                                                          amqpSettings)

        logger.debug ("""
   =======================================================================================
   ==  C O M P I L E (%s)
   =======================================================================================
   ==   user.username: (%s)
   ==   outputDir    : (%s)
   ==   logFile      : (%s)
   ==   amqp         : (%s)
   =======================================================================================""",
                      archivePath,
                      user.username,
                      unpack_dir,
                      log_file,
                      amqpSettings)
        GraysonCompiler.compile (models    = [ archivePath ],
                                 outputdir = unpack_dir,
                                 logDir    = unpack_dir,
                                 appHome   = unpack_dir,
                                 toLogFile = "log.txt",
                                 execute   = True,
                                 logLevel  = "debug",
                                 plugin    = executionMonitor)
    except ValueError, e:
        traceback.print_exc ()
        eventStream = EventStream (amqpSettings)
        eventStream.sendCompilationMessagesEvent (username = user.username,
                                                  flowId   = archive,
                                                  log      = log_file)
    except:
        traceback.print_exc ()
