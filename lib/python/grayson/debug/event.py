
import json
import logging
import time
import os

from grayson.net.amqp import GraysonAMQPTransmitter
from grayson.common.util import GraysonUtil

logger = logging.getLogger (__name__)

class EventStream (object):

    def __init__(self, amqpSettings, logRelPath=".", eventBufferSize=0):
        logger.info ("eventstream:amqpsettings: %s", amqpSettings)
        logger.info ("eventstream:logRelPath: %s", logRelPath)

        self.amqpSettings = amqpSettings
        self.count = 0
        self.eventBufferSize = eventBufferSize
        self.eventBuffer = []
        self.logRelPath = logRelPath
        '''
        if (isinstance (amqpSettings, int)):
            raise ValueError ("badness")
            '''

    def publish (self, event, aux={}):        
        logger.debug ("publishing: %s with amqp settings %s", event, self.amqpSettings)
        event = self.normalize (event)
        logger.debug ("event: %s", json.dumps (event))
        for key in aux:
            event [key] = aux [key]
        if self.eventBufferSize > 0:
            if len (self.eventBuffer) < self.eventBufferSize:
                self.eventBuffer.append (event)
                #logger.debug ("amqp-event-stream:buffered event: %s", event)
            else:
                self.flush (event)
        else:
            self.transmit (event)

    def flush (self, event):
        self.eventBuffer.append (event)
        self.transmit ({
                "clientId"   : event ["clientId"], 
                "flowId"     : event ["flowId"],
                "type"       : "composite",
                "events"     : self.eventBuffer,
                "time"       : time.time ()
                })
        del self.eventBuffer [:]

    def normalize (self, event):
        if "logdir" in event:
            logdir = event["logdir"]
            event["logdir"] = os.path.relpath (logdir, self.logRelPath)
        return GraysonUtil.relativize (object   = event,
                                       keys     = [ 'flowId', 'workdir', 'graph' ],
                                       username = event ['clientId'])

    def transmit (self, event):
        amqp = GraysonAMQPTransmitter (self.amqpSettings)
        text = json.dumps (event, indent=4)
        amqp.send ([ text ])
        self.count += 1
        logger.debug ("message count: %s",  self.count)

    def sendJobStatusEvent (self, username, flowId, jobid, status, logdir="", evt_time=None, aux={}):
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
                }, aux)

    def sendWorkflowEvent (self, username, flowId, graphPath, workdir="", aux={}):
        logger.debug ("event-stream:send:workflow-evt: user(%s) wfid(%s) graph(%s)", username, flowId, graphPath)
        self.publish ({ 
                "clientId" : username, 
                "flowId"   : flowId,
                "type"     : "workflow.structure",
                "workdir"  : workdir,
                "graph"    : graphPath
                }, aux)

    def sendSubworkflowEvent (self, username, flowId, graphPath, aux={}):
        logger.debug ("event-stream:send:subworkflow-evt: user(%s) wfid(%s) graph(%s)", username, flowId, graphPath)
        self.publish ({ 
                "clientId" : username, 
                "flowId"   : flowId,
                "type"     : "subworkflow.structure",
                "element"  : graphPath
                }, aux)
    
    def sendEndEvent (self, username, flowId, aux={}):
        logger.debug ("event-stream:send:end-evt: user(%s) wfid(%s)", username, flowId)
        self.flush ({
                "clientId" : username,
                "flowId"   : flowId,
                "type"     : "endEventStream",
                "time"     : time.time ()
                })

    def sendCompilationMessagesEvent (self, username, flowId, log, aux={}):
        logger.debug ("event-stream:send:compilation-error: user(%s) wfid(%s)", username, flowId)
        self.publish ({
                "clientId" : username,
                "flowId"   : flowId,
                "type"     : 'compilation-messages',
                "log"      : log,
                "time"     : time.time ()
                }, aux)

    def sendLogStructureEvent (self, username, flowId, log, aux={}):
        logger.debug ("event-stream:send:log-structure-evt: user(%s) wfid(%s), log(%s)", username, flowId, log)
        self.publish ({
                "clientId" : username,
                "flowId"   : flowId,
                "type"     : 'log.structure',
                "log"      : log,
                "time"     : time.time ()
                }, aux)
