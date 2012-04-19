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
from grayson.debug.grid import GridWorkflowMonitor
from grayson.debug.event import EventStream

from web.graysonapp.util import GraysonWebConst
from web.graysonapp.util import GraysonWebUtil
from web.graysonapp.util import StrUtil
from web.graysonapp.util import Workflow


''' #http://celeryproject.org/docs/django-celery/getting-started/first-steps-with-django.html '''

logger = logging.getLogger (__name__)

LOCK_EXPIRE = 60 * 5 # Lock expires in 5 minutes

class WorkflowMonitor (Task):
    name = "workflow.monitor"

    def run (self, username, workflowId, workdir, logRelPath=".", amqpPort=None, amqpQName=None, eventBufferSize=0, **kwargs):
        logger = self.get_logger (**kwargs)

        # The cache key is the task name and the MD5 digest of the workdir.
        workflow_digest = md5(workdir).hexdigest()
        lock_id = "%s-lock-%s" % (self.name, workflow_digest)

        # cache.add fails if if the key already exists
        acquire_lock = lambda: cache.add(lock_id, "true", LOCK_EXPIRE)
        # memcache delete is very slow, but we have to use it to take
        # advantage of using add() for atomic locking
        release_lock = lambda: cache.delete(lock_id)

        logger.debug("Monitoring workflow: %s" % workdir)
        if acquire_lock ():
            try:
                # Read and emit events so far, then loop continually until the workflow completes.
                monitor = GridWorkflowMonitor (workflowId, username, workdir, logRelPath, amqpPort, amqpQName, eventBufferSize)
                monitor.execute ()
            finally:
                release_lock()
        else:
            logger.debug(
                "Workflow %s is already being monitored by another worker. Emit events so far." % (
                    workdir))
            # Read and emit events so far, then exit.
            monitor = GridWorkflowMonitor (workflowId, username, workdir, logRelPath, amqpPort, amqpQName)
            monitor.execute (loop=False)

@task()
def MonitorWorkflow (workflowId, username, workdir, amqpPort=None, amqpQName=None):
    monitor = GridWorkflowMonitor (workflowId, username, workdir, amqpPort, amqpQName)
    monitor.execute (loop=False)

@task()
def ExecuteWorkflow (user, archive, archivePath, logRelPath=".", amqpPort=None, amqpQName=None):
    try:
        try:
            basename = os.path.basename (archive)
            unpack_dir = GraysonWebUtil.form_workflow_path (user, GraysonWebConst.UNPACK_EXT % basename)

            # If we don't open up permissions, using x509userproxy doesn't work. i.e. users can't run as themselves and write files here, for example.
            chmodCommand = "chmod -R 777 %s" % unpack_dir
            logger.debug ("setting output directory permissions: %s" % chmodCommand)
            os.system (chmodCommand)

            log_file = os.path.join (unpack_dir, "log.txt")
            executionMonitor = WorkflowMonitorCompilerPlugin (user.username, unpack_dir, logRelPath, amqpPort, amqpQName)

            logger.debug ("""
   =======================================================================================
   ==  C O M P I L E (%s)
   =======================================================================================
   ==   user.username: (%s)
   ==   outputDir    : (%s)
   ==   logFile      : (%s)
   ==   amqp.port    : (%s)
   =======================================================================================""",
                          archivePath,
                          user.username,
                          unpack_dir,
                          log_file,
                          amqpPort)
            GraysonCompiler.compile (models    = [ archivePath ],
                                     outputdir = unpack_dir,
                                     toLogFile = log_file,
                                     execute   = True,
                                     logLevel  = "debug",
                                     plugin    = executionMonitor)
        except ValueError, e:
            traceback.print_exc ()
            eventStream = EventStream (amqpPort, amqpQName)
            eventStream.sendCompilationMessagesEvent (username = user.username,
                                                      flowId   = archive,
                                                      log      = log_file)

        logger.debug ("""
   =======================================================================================
   ==  C O M P I L E (%s)
   =======================================================================================
   ==   user.username: (%s)
   ==     archivePath: (%s)
   ==   amqp.port    : (%s)
   =======================================================================================""",
                      archive,
                      user.username,
                      archivePath,
                      amqpPort)
    except:
        traceback.print_exc ()