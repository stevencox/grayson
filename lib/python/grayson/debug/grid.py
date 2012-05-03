#!/usr/bin/env python

import logging
import getopt
import glob
import json
import os
import re
import sys
import string
import traceback
import time

from grayson.common.util import GraysonUtil
from grayson.debug.event import EventStream

from Pegasus.tools import kickstart_parser


logger = logging.getLogger (__name__)
            
class GridWorkflow (object):

    def __init__(self, workdir):
        self.workdir = workdir

    def getJobOutput (self, subworkflows=[], jobid=None):
        result = None
        list = self.getOutputFiles (subworkflows, "%s.*?.out.000" % jobid)
        if list:
            result = list [0]
        return result

    def getOutputFiles (self, subworkflows=[], item=None):
        output = []
        path = []

        files = GraysonUtil.getFiles (self.workdir)
        
        '''    '''
        if len (subworkflows) > 0:
            pattern = subworkflows [0] 
        else:
            for sub in subworkflows:
                sub = sub.replace (".dax", "")
                path.append (".*?%s" % sub)
            pattern = "".join (path)

        if type (item) == unicode or type (item) == str:
            request = ".*?%s/%s" % (pattern, item)
            logger.debug ("_______________________: %s", request)
            output = GraysonUtil.findFilesByName (".*?%s/%s" % (pattern, item), files)
        elif type(item) == list:
            for output in item:
                partial = GraysonUtil.findFilesByName (".*?%s/%s" % (pattern, output), files)
                for element in partial:
                    output.append (element)
        return output

'''
The hope is to switch to Pegasus STAMPEDE when that's ready to go.
'''
class GridWorkflowMonitor (object):

    SUBMIT = "SUBMIT"
    EXECUTE = "EXECUTE"
    JOB_SUCCESS = "JOB_SUCCESS"
    JOB_FAILURE = "JOB_FAILURE"
    JOB_HELD = "JOB_HELD"
    DAGMAN_FINISHED = "DAGMAN_FINISHED"
    ALL_CODES = [ SUBMIT, EXECUTE, JOB_SUCCESS, JOB_FAILURE, DAGMAN_FINISHED ]

    STATUS_PENDING = "pending"
    STATUS_EXECUTING = "executing"
    STATUS_SUCCEEDED = "succeeded"
    STATUS_FAILED = "failed"

    def __init__(self, workflowId, username, workdir, logRelPath=".", amqpSettings=None, eventBufferSize=0):
        logger.debug ("gridworkflowmonitor:init")
        self.workflow = GridWorkflow (workdir)
        self.tracker = {}
        self.workflowId = workflowId
        self.username = username
        self.monitorRunning = False

        self.eventStream = EventStream (amqpSettings, logRelPath, eventBufferSize)

        self.transferBytesPattern = re.compile ('Stats: ([0-9]+(.[0-9]+)?)')
        self.transferDurationPattern = re.compile ('in ([0-9]+(.[0-9]+)?) seconds')
        self.transferRateUpPattern = re.compile ('Rate: ([0-9]+(.[0-9]+) [A-Za-z]+/s)')
        self.transferRateDownPattern = re.compile ('/s \(([0-9]+(.[0-9]+) [A-Za-z]+/s\))')

    def execute (self, loop=True):
        self.monitorRunning = True
        iteration = 0
        while self.monitorRunning:
            if iteration % 2 == 0:
                logger.debug ("   monitor: %s cycle: %s \ndir: %s", self.workflowId, self.workflow.workdir, iteration)
            logs = self.workflow.getOutputFiles ([], "jobstate.log")
            rootLog = os.path.join (self.workflow.workdir, "jobstate.log")            
            if logs:
                for out in logs:
                    track = 0
                    if out in self.tracker:
                        track = self.tracker [out]
                    try:
                        states = open (out, "r")
                        try:
                            count = 0
                            for line in states:
                                if count > track:
                                    logdir = os.path.dirname (out)
                                    self.detectEvent (logdir, line)
                                count += 1
                                self.tracker [out] = count
                        except IOError, e:
                            traceback.print_exc ()
                    finally:
                        states.close ()
            if loop:
                time.sleep (3)
            else:
                self.monitorRunning = False
                logger.debug ("debug:grid:endevent: user(%s) workflow(%s)", self.username, self.workflowId)
            iteration += 1

        self.eventStream.sendEndEvent (self.username, self.workflowId)

    def finish (self):
        self.monitorRunning = False
        logger.debug ("debug:grid:endevent: user(%s) workflow(%s)", self.username, self.workflowId)
        self.eventStream.sendEndEvent (self.username, self.workflowId)

    def accept (self, jobId):
        accept = True
        skip = [ 'clean_up',                  
		 'chmod',
		 'register_',
		 'create_dir_' ]
        for prefix in skip:
            if jobId.startswith (prefix):
                accept = False
                break
        return accept
        
    def sendEvent (self, logdir, evt_time, jobId, status):

        if self.accept (jobId) or status == GridWorkflowMonitor.STATUS_FAILED:
            aux = self.detectEventDetails (logdir, jobId, status)
            logdir = os.path.abspath (logdir)
            logger.debug ("--logdir: %s ", logdir)
            self.eventStream.sendJobStatusEvent (username = self.username,
                                                 flowId   = self.workflowId,
                                                 jobid    = jobId,
                                                 status   = status,
                                                 logdir   = logdir,
                                                 evt_time = evt_time,
                                                 aux      = aux)

    def detectEvent (self, logdir, line):
        if GraysonUtil.containsAny (line, GridWorkflowMonitor.ALL_CODES):
            parts = line.split (' ')
            logger.debug ("detect [%s]", line)
            time  = parts [0]
            jobId = parts [1]
            code  = parts [2]
            statusMap = {
                GridWorkflowMonitor.SUBMIT      : GridWorkflowMonitor.STATUS_PENDING,
                GridWorkflowMonitor.EXECUTE     : GridWorkflowMonitor.STATUS_EXECUTING,
                GridWorkflowMonitor.JOB_SUCCESS : GridWorkflowMonitor.STATUS_SUCCEEDED,
                GridWorkflowMonitor.JOB_FAILURE : GridWorkflowMonitor.STATUS_FAILED
                }
            if parts [3] == GridWorkflowMonitor.DAGMAN_FINISHED and logdir == self.workflow.workdir:
                status = parts [4]
                ''' end monitoring only if this is the root workflow '''
                self.monitorRunning = False
                exitCode = self.STATUS_SUCCEEDED if status == "0" else self.STATUS_FAILED
                self.sendEvent (logdir, time, jobId, exitCode) 
            else:
                if code in statusMap:
                    self.sendEvent (logdir, time, jobId, statusMap [code])
                    
    def detectEventDetails (self, logdir, jobId, status):
        aux = {}

        if jobId.startswith ('stage_in') or jobId.startswith ('stage_out'):
            path = os.path.join (logdir, "%s.in" % jobId)
            logger.debug ("opening path: %s", path)
            text = GraysonUtil.readFile (path)
            lines = text.split ('\n')
            if lines:
                transfers = []
                pair = 0
                #for line in lines:
                while len (lines) > ((pair * 4) + 4):

                    for line in lines:
                        logger.debug ("line: %s", line)

                    offset = pair * 4
                    
                    transfer = {
                        "sourceSite" : lines [offset + 0],
                        "sourceFile" : lines [offset + 1],
                        "destSite"   : lines [offset + 2],
                        "destFile"   : lines [offset + 3],
                        }
                    pair += 1
                    execution = self.getExecutionData (logdir, jobId)
                    if execution:
                        stdout = execution ['stdout']
                        transferred = GraysonUtil.getPrecompiledPattern (self.transferBytesPattern, stdout)
                        duration = GraysonUtil.getPrecompiledPattern (self.transferDurationPattern, stdout)
                        rateUp = GraysonUtil.getPrecompiledPattern (self.transferRateUpPattern, stdout)
                        rateDown = GraysonUtil.getPrecompiledPattern (self.transferRateDownPattern, stdout)
                        transfer ["bytes"] = transferred
                        transfer ["time"] = duration
                        transfer ["up"] = rateUp
                        transfer ["down"] = rateDown
                        logger.debug ("kickstart stdout/err: %s" + json.dumps (execution, indent=4))
                        logger.debug ("     transferred: %s duration: %s rateUp: %s rateDown: %s", transferred, duration, rateUp, rateDown)
                        transfers.append (transfer)
                aux ['transfer'] = transfers

                '''
                    transfer = {
                        "sourceSite" : lines [0],
                        "sourceFile" : lines [1],
                        "destSite"   : lines [2],
                        "destFile"   : lines [3],
                        }
                    execution = self.getExecutionData (logdir, jobId)
                    if execution:
                        stdout = execution ['stdout']
                        transferred = GraysonUtil.getPrecompiledPattern (self.transferBytesPattern, stdout)
                        duration = GraysonUtil.getPrecompiledPattern (self.transferDurationPattern, stdout)
                        rateUp = GraysonUtil.getPrecompiledPattern (self.transferRateUpPattern, stdout)
                        rateDown = GraysonUtil.getPrecompiledPattern (self.transferRateDownPattern, stdout)
                        transfer ["bytes"] = transferred
                        transfer ["time"] = duration
                        transfer ["up"] = rateUp
                        transfer ["down"] = rateDown
                        logger.debug ("kickstart stdout/err: %s" + json.dumps (execution, indent=4))
                        logger.debug ("     transferred: %s duration: %s rateUp: %s rateDown: %s", transferred, duration, rateUp, rateDown)
                        aux ['transfer'] = transfer
                        '''

        if status == GridWorkflowMonitor.STATUS_FAILED:
            execution = self.getExecutionData (logdir, jobId)
            if execution:
                aux ["detail"] = {
                    "stdout" : GraysonUtil.ceilingString (execution ["stdout"], maxLength=500, fromEnd=True),
                    "stderr" : GraysonUtil.ceilingString (execution ["stderr"], maxLength=500, fromEnd=True)
                    }

        dagLog = glob.glob (os.path.join (logdir, '*.dag.dagman.out'))
        dax = glob.glob (os.path.join (logdir, 'dax', '*.dax'))
        
        if len(dagLog) > 0 or len (dax) > 0:
            log = {}
            aux ['log'] = log
            if len (dagLog) > 0:
                log ['daglog'] = os.path.basename (dagLog [0])
            if len (dax) > 0:
                log ['dax'] = os.path.basename (dax [0])

        return aux

    def getExecutionData (self, logdir, jobId):
        obj = None
        kickstartPath = os.path.join (logdir, "%s.out.000" % jobId)
        logger.debug ("opening kickstartpath: %s", kickstartPath)
        kickstart = kickstart_parser.Parser (kickstartPath)
        logger.debug ("ks: %s", kickstartPath)
        if kickstart.open ():
            obj = kickstart.parse_stdout_stderr ()
            if obj and len(obj) > 0:
                obj = obj [0]
        return obj

