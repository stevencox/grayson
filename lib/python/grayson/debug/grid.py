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
from grayson.executor import Executor
from grayson.debug.stampede import EventScanner
from grayson.debug.stampede import Processor
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
            output = GraysonUtil.findFilesByName (".*?%s/%s" % (pattern, item), files)
        elif type(item) == list:
            for output in item:
                partial = GraysonUtil.findFilesByName (".*?%s/%s" % (pattern, output), files)
                for element in partial:
                    output.append (element)
        return output

class WorkflowMonitorDatabase (object):
    # TODO: yes, this is not thread safe. move to an amqp message, database, or other later.

    def flowPath (self, root):
        return os.path.join (root, 'workflows.txt')    

    def readFlows (self, root):
        fileName = self.flowPath (root)
        text = GraysonUtil.readFile (fileName)
        flows = []
        if text:
            flows = json.loads (text)
        return flows

    def writeFlows (self, root, flows):
        fileName = self.flowPath (root)
        workflowText = json.dumps (flows, indent=3, sort_keys=True)
        logger.debug (workflowText)
        GraysonUtil.writeFile (fileName, workflowText)

    def subscribeToWorkflow (self, root, workflow):
        flows = self.readFlows (root)
        flows.append (workflow)
        self.writeFlows (root, flows)

    def unsubscribeToWorkflow (self, root, workflow):
        flows = self.readFlows (root)
        for flow in flows:
            if flow ['workflowId'] == workflow ['workflowId']:
                flows.remove (flow)
        self.writeFlows (root, flows)






class EventDetailScanner (object):

    def __init__(self):
        self.transferBytesPattern = re.compile ('Stats: ([0-9]+(.[0-9]+)?)')
        self.transferDurationPattern = re.compile ('in ([0-9]+(.[0-9]+)?) seconds')
        self.transferRateUpPattern = re.compile ('Rate: ([0-9]+(.[0-9]+) [A-Za-z]+/s)')
        self.transferRateDownPattern = re.compile ('/s \(([0-9]+(.[0-9]+) [A-Za-z]+/s\))')

    def detectEventDetails (self, event, logdir, status):
        jobId = event.name
        aux = { 'sched_id' : event.sched_id }

        if not logdir:
            return aux

        if jobId.startswith ('stage_in') or jobId.startswith ('stage_out'):
            path = os.path.join (logdir, "%s.in" % jobId)
            #logger.debug ("opening path: %s", path)
            text = GraysonUtil.readFile (path)
            lines = text.split ('\n')
            if lines:
                transfers = []
                pair = 0
                while len (lines) > ((pair * 4) + 4):
                    '''
                    for line in lines:
                        logger.debug ("line: %s", line)
                        '''
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
                        '''
                        logger.debug ("kickstart stdout/err: %s" + json.dumps (execution, indent=4))
                        logger.debug ("     transferred: %s duration: %s rateUp: %s rateDown: %s", transferred, duration, rateUp, rateDown)
                        '''
                        transfers.append (transfer)
                aux ['transfer'] = transfers


        if status == WorkflowStatus.STATUS_FAILED:
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
        #logger.debug ("opening kickstartpath: %s", kickstartPath)
        kickstart = kickstart_parser.Parser (kickstartPath)
        #logger.debug ("ks: %s", kickstartPath)
        if kickstart.open ():
            obj = kickstart.parse_stdout_stderr ()
            if obj and len(obj) > 0:
                obj = obj [0]
        return obj

class WorkflowStatus (object):

    CONDOR_JOB_STATUS__RUNNING = 2

    SUBMIT = "SUBMIT"
    EXECUTE = "EXECUTE"
    JOB_SUCCESS = "JOB_SUCCESS"
    JOB_FAILURE = "JOB_FAILURE"
    JOB_HELD = "JOB_HELD"
    DAGMAN_FINISHED = "DAGMAN_FINISHED"

    STATUS_PENDING = "pending"
    STATUS_EXECUTING = "executing"
    STATUS_SUCCEEDED = "succeeded"
    STATUS_FAILED = "failed"

    STATUS_MAP = {
        SUBMIT      : STATUS_PENDING,
        EXECUTE     : STATUS_EXECUTING,
        JOB_SUCCESS : STATUS_SUCCEEDED,
        JOB_FAILURE : STATUS_FAILED
        }

class WorkflowMonitor (Processor):

    def __init__(self, username, workdir, workflowId, daxen, eventStream, bufferSize):
        logger.debug ("workflow-monitor: <init>")
        self.username      = username
        self.workdir       = workdir
        self.scanner       = EventScanner (workdir)
        self.detailScanner = EventDetailScanner ()
        self.workflowId    = workflowId
        self.daxen         = daxen
        self.maxTimestamp  = 0
        self.status        = None
        self.totalEvents   = 0
        self.cycleEventsA  = 0 # all
        self.cycleEventsT  = 0 # total

        self.isRunning = False
        self.isComplete = False

        self.examineWorkflow ()
        self.bufferSize = 0 if self.isRunning else bufferSize
        self.eventStream   = eventStream.getEventContext (bufferSize)

    def examineWorkflow (self):

        jobstatelog = os.path.join (self.workdir, 'jobstate.log')

        sched_id = 0
        def process (line):
            finishedTag = 'DAGMAN_FINISHED'
            schedIdTag = 'DAGMAN STARTED'
            
            index = line.find (schedIdTag)
            if index > -1:
                sched_id = line.split (' ')[-2]
                
            index = line.find (finishedTag)
            if index > -1:
                self.isComplete = True
                    
        text = GraysonUtil.readFile (jobstatelog, process)

        output = []
        executor = Executor ({
                'condorHome' : os.environ ['CONDOR_HOME'],
                'sched_id'   : sched_id
                })
        executor.execute (command   = "${condorHome}/bin/condor_q ${sched_id} -format '%s' JobStatus",
                          pipe      = True,
                          processor = lambda n : output.append (n))

        self.isRunning = ''.join (output) == WorkflowStatus.CONDOR_JOB_STATUS__RUNNING        

        logger.debug ("WorkflowMonitor - isRunning=%s, isComplete=%s", self.isRunning, self.isComplete) 

    def accepts (self, daxName):
        accepts = False
        if len(self.daxen) == 0: # no filters specified, accept everything.
            accepts = True
        else:
            if daxName:
                for key in self.daxen:
                    # starts with the filter and either (a) rest is '.dax' or (b) key does not contain '.' ... i.e. is not an indexed dax.
                    if daxName.find (key) == 0 and ( (len(daxName) == (len(key) + 4)) or (daxName.find('.') == -1) ):
                        accepts = True
                        break
        #logger.debug ("dax: %s, filter: %s, accepts: %s", daxName, self.daxen, accepts)
        return accepts

    def processEvent (self, event):
        self.totalEvents += 1
        self.cycleEventsT += 1
        if self.accepts (event.dax_file) or event.name.find ("subdax_") == 0:
            if event.state in WorkflowStatus.STATUS_MAP:
                logger.debug ("         -------(sendevent: %s)", event.name)
                self.sendEvent (event)
                self.cycleEventsA += 1

    def runCycle (self):
        maxTimestampIn = self.maxTimestamp
        self.cycleEventsA = 0
        self.cycleEventsT = 0
        self.status, self.maxTimestamp = self.scanner.getEvents (processor = self,
                                                                 since     = self.maxTimestamp,
                                                                 daxen     = self.daxen)
        if logger.isEnabledFor (logging.DEBUG):
            logger.debug ("monitor cycle: flow[%s] maxTimestamp[in->%s, out->%s] events[cycle-accepted->%s, cycle-all->%s, total->%s] daxen:%s wf[%s]",
                          self.workflowId, maxTimestampIn, self.maxTimestamp,
                          self.cycleEventsA, self.cycleEventsT, self.totalEvents, self.daxen, self.workflowId)
        return self.status

    def finish (self):
        logger.debug ("workflow-monitor.finish: send end event. workflow(%s)", self.workflowId)
        self.eventStream.sendEndEvent (self.username, self.workflowId)

    def sendEvent (self, event):
        status = self.translateExitCode (event)
        logdir = os.path.abspath (event.work_dir)
        self.sendTranslatedEvent (event, status, logdir)

    def sendTranslatedEvent (self, event, status, logdir):
        self.eventStream.sendJobStatusEvent (username = self.username,
                                             flowId   = self.workflowId,
                                             jobid    = event.name,
                                             status   = self.translateExitCode (event),
                                             logdir   = logdir,
                                             evt_time = event.timestamp,
                                             aux      = self.detailScanner.detectEventDetails (event, logdir, status))

    def translateExitCode (self, event):
        return WorkflowStatus.STATUS_MAP [event.state] if event.state in WorkflowStatus.STATUS_MAP else None

class WorkflowMonitorTask (Processor):

    def __init__(self, workflowRoot, amqpSettings = None, eventBufferSize = 10):
        logger.debug ("workflow-monitor-task<init>: amqpsettings: %s", amqpSettings)
        self.workflowRoot = workflowRoot
        self.eventStream = None
        self.eventStream = EventStream (amqpSettings    = amqpSettings,
                                        workflowRoot    = workflowRoot,
                                        eventBufferSize = eventBufferSize)
        self.monitors = {}
        self.workflowMonitorDatabase = WorkflowMonitorDatabase ()

    def addMonitor (self, workflow):
        logger.debug ("add monitor: %s", workflow)
        workflowId = workflow ['workflowId']
        username   = workflow ['username']
        workdir    = workflow ['workdir']
        daxList    = workflow ['daxen']
        bufferSize = workflow ['buffer']

        daxen = {}
        for dax in daxList:
            aDax = dax.replace (".dax", "")
            daxen [aDax] = aDax

        monitor = WorkflowMonitor (username, workdir, workflowId, daxen, self.eventStream, bufferSize)
        self.monitors [workflowId] = monitor

    def removeMonitor (self, monitorKey):
        logger.debug ("removing monitor: %s", monitorKey)
        del self.monitors [monitorKey]

    def updateMonitors (self):
        flows = self.workflowMonitorDatabase.readFlows (self.workflowRoot)
        '''
        if len(flows) > 0:
            logger.debug ("read workflows: %s", json.dumps (flows, indent=3, sort_keys=True)) 
            '''
        if flows:
            flowIds = {}
            newFlows = []
            for flow in flows:
                try:
                    workflowId = flow ['workflowId']
                    flowIds [workflowId] = flow

                    alreadyMonitored = False

                    if workflowId in self.monitors:
                        monitor = self.monitors [workflowId]
                        if monitor and monitor.workdir == flow['workdir']:
                            logger.debug ("already monitoring %s", workflowId)
                            alreadyMonitored = True

                    if not alreadyMonitored:
                        newFlows.append (flow)
                except:
                    logger.error ("encountered error adding monitor for flow: %s", flow)
                    traceback.print_exc ()

            for flow in newFlows:
                logger.debug ("adding monitor for %s", workflowId)
                self.addMonitor (flow)

            keys = self.monitors.iterkeys ()
            for key in keys:
                try:
                    logger.debug ("checking status of %s", key)
                    if not key in flowIds:
                        logger.debug ("removing monitor for %s", key)
                        self.removeMonitor (key)
                except:
                    traceback.print_exc ()
                    logger.error ("encounered error removing monitor: %s", key)

    def execute (self, loop=True):
        '''
        TODO: check if the root dag's in condor. If not, the workflow was aborted. Report somehow and stop monitoring.
        '''
        running = True
        while running:
            try:
                keys = iter (self.monitors.keys ())
                for key in keys:
                    monitor = self.monitors [key]
                    if monitor:
                        try:
                            finished = monitor.runCycle ()
                            if finished or monitor.isComplete:
                                monitor.finish ()
                                self.removeMonitor (key)
                                self.workflowMonitorDatabase.unsubscribeToWorkflow (self.workflowRoot, { 'workflowId' : key })
                        except:
                            traceback.print_exc ()
                self.updateMonitors ()
            except:
                traceback.print_exc ()
            time.sleep (1)

if __name__ == "__main__":
    logging.basicConfig ()
    __name__ = "stampede"
    logger.setLevel (logging.DEBUG)
    logging.getLogger('grayson.debug.event').setLevel (logging.ERROR)
    logging.getLogger('grayson.debug.stampede').setLevel (logging.ERROR)
    logging.getLogger('sqlalchemy.engine').setLevel (logging.ERROR)
    logger.info ("argv: %s", json.dumps (sys.argv))

    workdir = sys.argv [1]
    monitor = WorkflowMonitorTask (workdir) #'var/workflow') #'lib/python/grayson/debug')
    monitor.execute ()

''' python lib/python/grayson/debug/grid2.py x '''
