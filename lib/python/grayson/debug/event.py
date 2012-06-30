
import json
import logging
import time
import os

from grayson.net.amqp import GraysonAMQPTransmitter
from grayson.common.util import GraysonUtil

logger = logging.getLogger (__name__)

class EventContext (object):
    def __init__(self, stream, bufferSize=0):
        self.bufferSize = bufferSize
        self.eventBuffer = []
        self.stream = stream

    def sendJobStatusEvent (self, username, flowId, jobid, status, logdir="", evt_time=None, aux={}):
        self.stream.sendJobStatusEvent (username, flowId, jobid, status, logdir, evt_time, aux, context=self)

    def sendWorkflowEvent (self, username, flowId, graphPath, workdir="", aux={}):
        self.stream.sendWorkflowEvent (username, flowId, graphPath, workdir, aux, context=self)

    def sendSubworkflowEvent (self, username, flowId, graphPath, aux={}):
        self.stream.sendSubworkflowEvent (username, flowId, graphPath, aux, context=self)
    
    def sendEndEvent (self, username, flowId, aux={}):
        self.stream.sendEndEvent (username, flowId, aux, context=self)

    def sendCompilationMessagesEvent (self, username, flowId, log, aux={}):
        self.stream.sendCompilationMessagesEvent (username, flowId, log, aux, context=self)

    def sendLogStructureEvent (self, username, flowId, log, aux={}):
        self.stream.sendLogStructureEvent (username, flowId, log, aux, context=self)


class EventStream (object):

    def __init__(self, amqpSettings, workflowRoot=".", eventBufferSize=0):
        logger.info ("eventstream:amqpsettings: %s", amqpSettings)
        logger.info ("eventstream:workflowRoot: %s", workflowRoot)

        self.amqpSettings = amqpSettings
        self.count = 0
        self.workflowRoot = workflowRoot

    def getEventContext (self, bufferSize=0):
        return EventContext (stream     = self,
                             bufferSize = bufferSize)

    def publish (self, event, aux, context):        
        logger.debug ("publishing: %s with amqp settings %s", event, self.amqpSettings)
        event = self.normalize (event)
        logger.debug ("event: %s", json.dumps (event))
        for key in aux:
            event [key] = aux [key]
        if context.bufferSize > 0:
            if len (context.eventBuffer) < context.bufferSize:
                context.eventBuffer.append (event)
                #logger.debug ("amqp-event-stream:buffered event: %s", event)
            else:
                self.flush (event, context)
        else:
            self.transmit (event)

    def flush (self, event, context):
        logger.debug ("event-stream: ==============> flush")
        context.eventBuffer.append (event)
        self.transmit ({
                "clientId"   : event ["clientId"], 
                "flowId"     : event ["flowId"],
                "type"       : "composite",
                "events"     : context.eventBuffer,
                "time"       : time.time ()
                })
        del context.eventBuffer [:]

    def normalize (self, event):
        if "logdir" in event:
            logdir = event["logdir"]
            event["logdir"] = os.path.relpath (logdir, self.workflowRoot)
        return GraysonUtil.relativize (object   = event,
                                       keys     = [ 'flowId', 'workdir', 'graph' ],
                                       username = event ['clientId'])


    def transmit (self, event):
        text = json.dumps (event, indent=3, sort_keys=True)
        if logger.isEnabledFor (logging.DEBUG):
            logger.debug ('event-stream.transmit: %s', text)

        if self.amqpSettings:
            amqp = GraysonAMQPTransmitter (self.amqpSettings)
            amqp.send ([ text ])

        self.count += 1
        logger.debug ("message count: %s",  self.count)

    def sendJobStatusEvent (self, username, flowId, jobid, status, logdir="", evt_time=None, aux={}, context=None):
        if not evt_time:
            evt_time = time.time ()
        logger.debug ("event-stream:send:job-status: user(%s) wfid(%s) jobid(%s) status(%s) logdir(%s) time(%s)",
                       username, flowId, jobid, status, logdir, evt_time)
        self.publish ({
                "clientId" : username, 
                "flowId"   : flowId,
                "type"     : "jobstatus",
                "job"      : jobid,
                "time"     : evt_time,
                "state"    : status,
                "logdir"   : logdir
                }, aux, context)

    def sendWorkflowEvent (self, username, flowId, graphPath, workdir="", aux={}, context=None):
        logger.debug ("event-stream:send:workflow-evt: user(%s) wfid(%s) graph(%s)", username, flowId, graphPath)
        self.publish ({ 
                "clientId" : username, 
                "flowId"   : flowId,
                "type"     : "workflow.structure",
                "workdir"  : workdir,
                "graph"    : graphPath
                }, aux, context)

    def sendSubworkflowEvent (self, username, flowId, graphPath, aux={}, context=None):
        logger.debug ("event-stream:send:subworkflow-evt: user(%s) wfid(%s) graph(%s)", username, flowId, graphPath)
        self.publish ({ 
                "clientId" : username, 
                "flowId"   : flowId,
                "type"     : "subworkflow.structure",
                "element"  : graphPath
                }, aux, context)
    
    def sendEndEvent (self, username, flowId, aux={}, context=None):
        logger.debug ("event-stream:send:end-evt: user(%s) wfid(%s)", username, flowId)
        self.flush ({
                "clientId" : username,
                "flowId"   : flowId,
                "type"     : "endEventStream",
                "time"     : time.time ()
                }, context)

    def sendCompilationMessagesEvent (self, username, flowId, log, aux={}, context=None):
        logger.debug ("event-stream:send:compilation-error: user(%s) wfid(%s)", username, flowId)
        self.publish ({
                "clientId" : username,
                "flowId"   : flowId,
                "type"     : 'compilation-messages',
                "log"      : log,
                "time"     : time.time ()
                }, aux, context)

    def sendLogStructureEvent (self, username, flowId, log, aux={}, context=None):
        logger.debug ("event-stream:send:log-structure-evt: user(%s) wfid(%s), log(%s)", username, flowId, log)
        self.publish ({
                "clientId" : username,
                "flowId"   : flowId,
                "type"     : 'log.structure',
                "log"      : log,
                "time"     : time.time ()
                }, aux, context)
