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
from grayson.executor import Executor
from grayson.compiler.compiler import GraysonCompiler
from grayson.compiler.compiler import CompilerPlugin
from grayson.packager import GraysonPackager
from grayson.debug.event import EventStream
from grayson.common.util import GraysonUtil
from web.graysonapp.util import StrUtil
from django.utils.translation import ugettext as _
from grayson.debug.grid import WorkflowMonitorTask
from grayson.debug.grid import WorkflowMonitorDatabase

logger = logging.getLogger (__name__)

''' Compiler Plugin '''
class WorkflowMonitorCompilerPlugin (object):

    def __init__(self, username, graphPrefix, workflowRoot=".", amqpSettings=None):
        self.username = username
        self.graphPathPrefix = graphPrefix
        self.eventStream = EventStream (amqpSettings, workflowRoot).getEventContext ()
        self.amqpSettings = amqpSettings
        self.workflowRoot = workflowRoot
        self.workflowMonitorDatabase = WorkflowMonitorDatabase ()
        logger.debug ("workflowmonitorcompilerplugin:amqpsettings: %s", amqpSettings)

    def notifyShellEvent (self, line, outputWorkflowPath):
        logger.info ("|| %s", line)
        jobid = None
        status = None
        workdirMarker = "pegasus-status -l "
        if workdirMarker in line:
            ''' this is a grid job '''
            workDir = line [ line.rfind (workdirMarker) + len (workdirMarker) : ]
            workDir = workDir.rstrip ()
            logger.info ("starting grid monitor workflowId: %s, username: %s, workDir: %s", outputWorkflowPath, self.username, workDir)

            idparts = workDir.split (os.sep)
            if len(idparts) >= 7:
                workflowName = idparts [len(idparts)-2]
                workflowId = os.path.join (idparts [len(idparts)-6],
                                           workflowName).replace ('.dax', '')
                self.workflowMonitorDatabase.subscribeToWorkflow (
                    self.workflowRoot,
                    {
                        "username"    : self.username,
                        "workflowId"  : workflowId,
                        "workdir"     : workDir,
                        "daxen"       : [],
                        "buffer"      : 0
                        })

        elif "Executing JOB" in line:
            jobid = StrUtil.between (line, "::", ":")
            if " " in jobid:
                jobid = StrUtil.before (jobid, " ")
                status = "running"
                logger.info ('--grayson:shell-compilerplugin: got executing %s %s', jobid, status)                
        elif "Returned with" in line:
            jobid = StrUtil.between (line, " JOB ", "_")
            exitcode = ""
            try:
                statustext = StrUtil.afterlast (line, "Returned with ").rstrip ()
                status = int (statustext)
                logger.info ('--grayson:shell-compilerplugin: got status %s %s %s', jobid, statustext, status)
            except:
                logger.error ("cant parse exit code")
                traceback.print_exc ()
                logger.info (' -- got returned with %s %s', jobid, status)
        if jobid and status != None:
            logger.info ("--grayson:shell-compilerplugin: notifying got returned with %s %s", jobid, status)
            self.eventStream.sendJobStatusEvent (self.username, outputWorkflowPath, jobid, status)

    def notifyWorkflowCreation (self, workflowGraph, outputWorkflowPath, topWorkflow=False):
        if topWorkflow:
            logger.info ("--grayson:shell-compilerplugin: notifying workflow creation: %s", workflowGraph)
            graphPath = "%s.graphml" % workflowGraph
            graphPath = os.path.join (self.graphPathPrefix, graphPath)
            self.eventStream.sendWorkflowEvent (self.username, outputWorkflowPath, graphPath, outputWorkflowPath)
        else:
            logger.info ("outputWorkflowPath: %s graph: %s", outputWorkflowPath, workflowGraph)
            self.eventStream.sendSubworkflowEvent (self.username, outputWorkflowPath, workflowGraph)
