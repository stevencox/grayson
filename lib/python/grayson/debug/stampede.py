
import decimal
import json
import os
import re
import sys
import logging
import subprocess
import traceback

from grayson.common.util import GraysonUtil

logger = logging.getLogger (__name__)

def figureImportOutPath ():
    bin_dir = os.path.join (os.environ['PEGASUS_HOME'], 'bin')
    pegasus_config = os.path.join(bin_dir, "pegasus-config") + " --noeoln --python"
    lib_dir = subprocess.Popen(pegasus_config, stdout=subprocess.PIPE, shell=True).communicate()[0]
    pegasus_config = os.path.join(bin_dir, "pegasus-config") + " --noeoln --python-externals"
    lib_ext_dir = subprocess.Popen(pegasus_config, stdout=subprocess.PIPE, shell=True).communicate()[0]
    os.sys.path.insert(0, lib_ext_dir)
    os.sys.path.insert(0, lib_dir)

if __name__ == "__main__":
    figureImportOutPath ()

from netlogger.analysis.workflow.stampede_statistics import StampedeStatistics
from netlogger.analysis.schema.schema_check import SchemaVersionError
from netlogger.analysis.schema.stampede_schema import *
from Pegasus.tools import utils
from Pegasus.tools import db_utils
from Pegasus.plots_stats import utils as stats_utils

class WorkflowEvent:
    ''' A workflow event '''
    def __init__(self):
        self.name = None
        self.site = None
        self.sched_id = None
        self.work_dir = None
        self.timestamp = None
        self.exitcode = None
        self.hostname = None
        self.is_dax = False
        self.dax_file = None
        self.state = None
        self.stdout = None
        self.stderr = None

class WorkflowEventEncoder(json.JSONEncoder):
    ''' Encode a workflow event as JSON '''
    def default(self, j):
        val = None
        if hasattr (j, "__dict__"):
            val = j.__dict__
        elif isinstance (j, decimal.Decimal):
            val = float (j)
        else:
            val = json.JSONEncoder.default (self, j)
        return val        
        
class StatsUtil (object):
    @staticmethod
    def formDaxName (workdir):
        result = None
        if workdir:
            workdir = os.path.basename (workdir)
            if '_' in workdir:
                index = workdir.find ('_')
                val = workdir [index + 1:]
                val = val.replace ("gid", ".")
                match = re.match("([\w-]+)\.?(\d+)\.?(\d+)?", val)
                if match:
                    groups = match.groups ()
                    result = '.'.join ([ groups [0], groups [1] ])
        return result

class EventScannerException (Exception):
    def __init__(self, value):
        self.parameter = value
    def __str__(self):
        return repr (self.parameter)

class EventScanner (object):
    ''' Stampede event scanner '''

    DAX_START = "dax-start"
    DAX_END = "dax-end"

    def __init__(self, submit_dir):
        ''' initialize - connect to the database. '''
        logger.debug ("event-scanner:<init> submit_dir: %s", submit_dir)
        properties = os.path.join (submit_dir, "grayson.stampede.properties")
        properties = None
	self.db_url, self.wf_uuid = db_utils.get_db_url_wf_uuid (submit_dir, properties)
        logger.debug ("dburl=(%s) wf_uuid=(%s)", self.db_url, self.wf_uuid)

        self.database = StampedeStatistics (self.db_url, True)
        self.database.initialize (self.wf_uuid)
        self.totalMessages = 0

    def createWorkflowEvent (self, record): 

        ''' Map a result set into an event object. '''
        event = WorkflowEvent ()
        event.name = record.exec_job_id
        event.is_dax = record.exec_job_id.find ('subdax_') == 0
        event.site = record.site
        event.timestamp = record.timestamp
        event.exitcode = utils.raw_to_regular (record.exitcode)
        event.hostname = record.hostname
        event.sched_id = record.sched_id
        event.work_dir = os.path.abspath (record.work_dir)
        event.work_dir = event.work_dir.replace ("work/outputs", "work")
        event.dax_file = os.path.basename (record.dax_file)  #os.path.basename (record.dax_file) if record.dax_file else StatsUtil.formDaxName (event.workdir)
        event.state = record.state
        event.work_dir = record.work_dir 
        event.stdout = record.stdout_file
        event.stderr = record.stderr_file
        
        #logger.debug (json.dumps (event, sort_keys=True, indent=3, cls=WorkflowEventEncoder))

        return event

        '''
SELECT job.job_id AS job_job_id,
       job.exec_job_id AS job_exec_job_id,
       job_instance.site AS job_instance_site,
       job_instance.sched_id AS job_instance_sched_id,
       job_instance.stdout_file AS job_instance_stdout_file,
       job_instance.stderr_file AS job_instance_stderr_file,
       job_instance.exitcode AS job_instance_exitcode,
       CAST(jobstate.timestamp AS FLOAT) AS TIMESTAMP,
       jobstate.state AS jobstate_state,
       host.hostname AS host_hostname,
       workflow.user AS workflow_user,
       workflow.dax_file AS workflow_dax_file,
       workflow.submit_dir AS work_dir
FROM job, job_instance, jobstate, HOST, workflow
WHERE job.job_id = job_instance.job_id
  AND job_instance.host_id = HOST.host_id
  AND job_instance.job_instance_id = jobstate.job_instance_id
  AND job.wf_id = workflow.wf_id
  AND jobstate.TIMESTAMP > ?
  AND NOT ((job_instance.exitcode = ?
            OR job_instance.exitcode = ?)
           AND (jobstate.state = ?
                OR jobstate.state = ?))
  AND (job.exec_job_id NOT LIKE ?
       OR job.exec_job_id LIKE ?)
  AND workflow.dax_file LIKE ?
  AND job.exec_job_id NOT LIKE ?
  AND job.exec_job_id NOT LIKE ?
  AND job.exec_job_id NOT LIKE ?
  AND job.exec_job_id NOT LIKE ?
ORDER BY jobstate.TIMESTAMP
'''
    def selectWorkflowEvents (self, since = 0, daxen = {}, jobFilter = None):
        ''' Select events from the stampede schema. '''
        query = self.database.session.query (Job.job_id,
                                             Job.exec_job_id,
                                             JobInstance.site,
                                             JobInstance.sched_id,
                                             JobInstance.stdout_file,
                                             JobInstance.stderr_file,
                                             JobInstance.exitcode,
                                             cast (Jobstate.timestamp, Float).label ('timestamp'),
                                             Jobstate.state,
                                             Host.hostname,
                                             Workflow.user,
                                             Workflow.dax_file,
                                             Workflow.submit_dir.label ('work_dir')) # unfortunate name mismatch between schema and existing code.
        query = query.filter (Job.job_id == JobInstance.job_id,
                              JobInstance.host_id == Host.host_id,
                              JobInstance.job_instance_id == Jobstate.job_instance_id,
                              Job.wf_id == Workflow.wf_id,
                              Jobstate.timestamp > since)
        query = query.order_by (JobInstance.sched_id, Jobstate.timestamp)

        ''' don't include intermediate statuses '''
        query = query.filter (not_(and_(or_(JobInstance.exitcode == 0, JobInstance.exitcode == 1),
                                        or_(Jobstate.state == 'SUBMIT', Jobstate.state == 'EXECUTE'))))
                                        

        ''' ensure that either (a) the event does not pertain to a subdax or that,
                               (b) if it does, the subdax is one in the list of daxen  '''
        filters = []
        for dax in daxen:
            filters.append (Job.exec_job_id.like ('subdax_%s%%' % dax))
        query = query.filter (or_( not_(Job.exec_job_id.like ('subdax_%')),
                                   or_(*tuple (filters))))

        ''' ensure dax_file of this event matches one of the daxen in the filter '''
        filters = []
        for dax in daxen:
            filters.append (Workflow.dax_file.like ('%%%s%%' % dax))
        query = query.filter (or_ (*tuple (filters)))
        
        ''' ignore job prefixes in the job filter. '''
        if jobFilter:
            for pattern in jobFilter:
                query = query.filter (not_ (Job.exec_job_id.like ('%s%%' % pattern)))

        ''' return the cursor. '''
        return query.all ()

    def getWorkflowStatus (self):
        ''' Find out if the workflow is still running '''
        return self.database.session.query (Workflowstate.status).filter (Workflow.wf_id == Workflowstate.wf_id,
                                                                          Workflow.wf_id == Workflow.root_wf_id,
                                                                          Workflowstate.state == 'WORKFLOW_TERMINATED').first ()
    def getEvents (self,
                   processor,
                   wf_uuid       = None,
                   jobFilter     = [ 'clean_up', 'chmod', 'register_', 'create_dir_' ],
                   since         = 0,
                   daxen         = {}):        
        ''' Get events for the workflow since a given timestamp. '''
        max_timestamp = since

        status = self.getWorkflowStatus ()
        events = self.selectWorkflowEvents (since, daxen, jobFilter)
        count = 0
        for event in events:
            processor.processEvent (self.createWorkflowEvent (event))
            max_timestamp = max (max_timestamp, event.timestamp)
            count += 1
        self.totalMessages += count

        if logger.isEnabledFor (logging.DEBUG):            
            logger.debug ("=====================================================================================================")
            logger.debug ("==        events: cycle=%s total=%s", count, self.totalMessages)
            logger.debug ("==  total events: %s ", count)
            logger.debug ("== max_timestamp: %s ", max_timestamp)
            logger.debug ("=====================================================================================================")
        return status, max_timestamp

    def emitJSON (self, obj):
        return json.dumps (obj,
                           cls       = WorkflowEventEncoder,
                           indent    = 2,
                           sort_keys = True)

''' Abstract pattern for a processor '''
class Processor (object):
    def processEvent (self, event):
        pass

''' Buffered processor '''
class BufferProcessor (Processor):
    def __init__(self):
        self.buffer = []
    def processEvent (self, event):
        self.buffer.append (event)

''' For debugging purposes. '''
class DebugProcessor (Processor):
    def __init__ (self, daxFilter = None):
        self.daxFilter = daxFilter
    def processEvent (self, event):
        if not daxFilter or event.dax_file == self.daxFilter:
            logger.debug ("event=>(%s)",
                          json.dumps (event,
                                      cls       = WorkflowEventEncoder,
                                      indent    = 2,
                                      sort_keys = True))
            
if __name__ == "__main__":
    logging.basicConfig ()
    __name__ = "stampede"
    logger.setLevel (logging.DEBUG)
    logger.info ("argv: %s", json.dumps (sys.argv))

    
    subdir = sys.argv [1]
    daxFilter = None if len (sys.argv) < 3 else sys.argv [2]
    if daxFilter == "-":
        daxFilter = None

    since = 0 if len (sys.argv) < 4 else int(sys.argv [3])
    scanner = EventScanner (subdir)
    status, max_timestamp = scanner.getEvents (wf_uuid   = scanner.wf_uuid,
                                       since     = since,
                                       processor = DebugProcessor (daxFilter))
    logger.debug ("max_timestamp=%s", max_timestamp)


