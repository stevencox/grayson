
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

def figureOutPath ():
    # Initialize logging object 
    bin_dir = os.path.join (os.environ['PEGASUS_HOME'], 'bin')
    pegasus_config = os.path.join(bin_dir, "pegasus-config") + " --noeoln --python"
    lib_dir = subprocess.Popen(pegasus_config, stdout=subprocess.PIPE, shell=True).communicate()[0]
    pegasus_config = os.path.join(bin_dir, "pegasus-config") + " --noeoln --python-externals"
    lib_ext_dir = subprocess.Popen(pegasus_config, stdout=subprocess.PIPE, shell=True).communicate()[0]
    os.sys.path.insert(0, lib_ext_dir)
    os.sys.path.insert(0, lib_dir)

if __name__ == "__main__":
    figureOutPath ()

from netlogger.analysis.workflow.stampede_statistics import StampedeStatistics
from netlogger.analysis.schema.schema_check import SchemaVersionError
from netlogger.analysis.schema.stampede_schema import *
from Pegasus.tools import utils
from Pegasus.tools import db_utils
from Pegasus.plots_stats import utils as stats_utils

class JobStatistics:
    def __init__(self):
        self.name = None
        self.site = None
        self.kickstart = None
        self.sched_id = None
        self.work_dir = None
        self.start_time = None
        self.remote_cpu_time = None
        self.runtime = None
        self.retry_count = 0
        self.exitcode = None
        self.hostname = None

        self.is_dax = False

        self.condorQlen = None
        self.seqexec = None
        self.seqexec_delay = None
        self.resource = None
        self.post = None
        self.condor_delay = None
        self.multiplier_factor = None
        self.kickstart_mult = None

class JobStatEncoder(json.JSONEncoder):
    def default(self, j):
        val = None
        if hasattr (j, "__dict__"):
            val = j.__dict__
        elif isinstance (j, decimal.Decimal):
            val = float (j)
        else:
            val = json.JSONEncoder.default (self, j)
        return val        
        
class GraysonStampedeStatistics ():

    ROOT_DIR_PAT = re.compile ('([0-9]{8})T')

    def __init__(self):
        pass

    def get_max_timestamp (self, database):
        q = database.session.query ( func.max (Jobstate.timestamp) )
        q = q.filter (JobInstance.job_id == Job.job_id)
        q = q.filter (Job.wf_id.in_(database._wfs))
        q = q.order_by (JobInstance.job_submit_seq)
        return q.scalar ()

    def get_job_statistics (self, database, since = 0):

        sq_1 = database.session.query(func.min(Jobstate.timestamp))
        sq_1 = sq_1.filter(Jobstate.job_instance_id == JobInstance.job_instance_id).correlate(JobInstance)
        sq_1 = sq_1.filter(or_(Jobstate.state == 'GRID_SUBMIT', Jobstate.state == 'GLOBUS_SUBMIT',
                                Jobstate.state == 'EXECUTE'))
        sq_1 = sq_1.subquery()
        
        sq_2 = database.session.query(Jobstate.timestamp)
        sq_2 = sq_2.filter(Jobstate.job_instance_id == JobInstance.job_instance_id).correlate(JobInstance)
        sq_2 = sq_2.filter(Jobstate.state == 'SUBMIT')
        sq_2 = sq_2.subquery()
        
        sq_3 = database.session.query(func.min(Jobstate.timestamp))
        sq_3 = sq_3.filter(Jobstate.job_instance_id == JobInstance.job_instance_id).correlate(JobInstance)
        sq_3 = sq_3.filter(Jobstate.state == 'EXECUTE')
        sq_3 = sq_3.subquery()
        
        sq_4 = database.session.query(func.min(Jobstate.timestamp))
        sq_4 = sq_4.filter(Jobstate.job_instance_id == JobInstance.job_instance_id).correlate(JobInstance)
        sq_4 = sq_4.filter(or_(Jobstate.state == 'GRID_SUBMIT', Jobstate.state == 'GLOBUS_SUBMIT'))
        sq_4 = sq_4.subquery()
        
        sq_5 = database.session.query(func.sum(Invocation.remote_duration))
        sq_5 = sq_5.filter(Invocation.job_instance_id == JobInstance.job_instance_id).correlate(JobInstance)
        sq_5 = sq_5.filter(Invocation.wf_id == Job.wf_id).correlate(Job)
        sq_5 = sq_5.filter(Invocation.task_submit_seq >= 0)
        sq_5 = sq_5.group_by().subquery()
        
        sq_6 = database.session.query(Jobstate.timestamp)
        sq_6 = sq_6.filter(Jobstate.job_instance_id == JobInstance.job_instance_id).correlate(JobInstance)
        sq_6 = sq_6.filter(Jobstate.state == 'POST_SCRIPT_TERMINATED')
        sq_6 = sq_6.subquery()
        
        sq_7 = database.session.query(func.max(Jobstate.timestamp))
        sq_7 = sq_7.filter(Jobstate.job_instance_id == JobInstance.job_instance_id).correlate(JobInstance)
        sq_7 = sq_7.filter(or_(Jobstate.state == 'POST_SCRIPT_STARTED', Jobstate.state == 'JOB_TERMINATED'))
        sq_7 = sq_7.subquery()
        
        sq_8 = database.session.query(func.max(Invocation.exitcode))
        sq_8 = sq_8.filter(Invocation.job_instance_id == JobInstance.job_instance_id).correlate(JobInstance)
        sq_8 = sq_8.filter(Invocation.wf_id == Job.wf_id).correlate(Job)
        sq_8 = sq_8.filter(Invocation.task_submit_seq >= 0)
        sq_8 = sq_8.group_by().subquery()
        
        JobInstanceSub = orm.aliased(JobInstance)
        
        sq_9 = database.session.query(Host.hostname)
        sq_9 = sq_9.filter(JobInstanceSub.job_instance_id == JobInstance.job_instance_id).correlate(JobInstance)
        sq_9 = sq_9.filter(Host.host_id == JobInstanceSub.host_id)
        sq_9 = sq_9.subquery()
        
        sq_10 = database.session.query(func.sum(Invocation.remote_duration * JobInstance.multiplier_factor))
        sq_10 = sq_10.filter(Invocation.job_instance_id == JobInstance.job_instance_id).correlate(JobInstance)
        sq_10 = sq_10.filter(Invocation.wf_id == Job.wf_id).correlate(Job)
        sq_10 = sq_10.filter(Invocation.task_submit_seq >= 0)
        sq_10 = sq_10.group_by().subquery()
        
        sq_11 = database.session.query(func.sum(Invocation.remote_cpu_time))
        sq_11 = sq_11.filter(Invocation.job_instance_id == JobInstance.job_instance_id).correlate(JobInstance)
        sq_11 = sq_11.filter(Invocation.wf_id == Job.wf_id).correlate(Job)
        sq_11 = sq_11.filter(Invocation.task_submit_seq >= 0)
        sq_11 = sq_11.group_by().subquery()
        
        sq_12 = database.session.query(func.sum(Invocation.start_time))
        sq_12 = sq_12.filter(Invocation.job_instance_id == JobInstance.job_instance_id).correlate(JobInstance)
        sq_12 = sq_12.filter(Invocation.wf_id == Job.wf_id).correlate(Job)
        sq_12 = sq_12.filter(Invocation.task_submit_seq >= 0)
        sq_12 = sq_12.group_by().subquery()
        
        q = database.session.query(Job.job_id, JobInstance.job_instance_id, JobInstance.job_submit_seq,
            Job.exec_job_id.label('job_name'), JobInstance.site,
            cast(sq_1.as_scalar() - sq_2.as_scalar(), Float).label('condor_q_time'),
            cast(sq_3.as_scalar() - sq_4.as_scalar(), Float).label('resource_delay'),
            cast(JobInstance.local_duration, Float).label('runtime'),
#very bad   cast(Invocation.start_time, Float).label('start_time'),
            cast(sq_12.as_scalar(), Float).label('start_time'),
            cast(sq_5.as_scalar(), Float).label('kickstart'),
            cast(sq_6.as_scalar() - sq_7.as_scalar(), Float).label('post_time'),
            cast(JobInstance.cluster_duration, Float).label('seqexec'),
            sq_8.as_scalar().label('exit_code'),
            sq_9.as_scalar().label('host_name'),
            JobInstance.multiplier_factor,
            cast(sq_10.as_scalar(), Float).label('kickstart_multi'),
            sq_11.as_scalar().label('remote_cpu_time'),
            cast(JobInstance.work_dir, String).label ('work_dir'),
            cast(JobInstance.sched_id, String).label ('sched_id'))
        q = q.filter(JobInstance.job_id == Job.job_id)
        q = q.filter(Job.wf_id.in_(database._wfs))
        q = q.order_by(JobInstance.job_submit_seq)

        return q.all()

    def getJobStats (self, database, since = 0):
        sq_8 = database.session.query(func.max(Invocation.exitcode))
        sq_8 = sq_8.filter(Invocation.job_instance_id == JobInstance.job_instance_id).correlate(JobInstance)
        sq_8 = sq_8.filter(Invocation.wf_id == Job.wf_id).correlate(Job)
        sq_8 = sq_8.filter(Invocation.task_submit_seq >= 0)
        sq_8 = sq_8.group_by().subquery()

        JobInstanceSub = orm.aliased(JobInstance)
        
        sq_9 = database.session.query(Host.hostname)
        sq_9 = sq_9.filter(JobInstanceSub.job_instance_id == JobInstance.job_instance_id).correlate(JobInstance)
        sq_9 = sq_9.filter(Host.host_id == JobInstanceSub.host_id)
        sq_9 = sq_9.subquery()

        sq_11 = database.session.query(func.sum(Invocation.remote_cpu_time))
        sq_11 = sq_11.filter(Invocation.job_instance_id == JobInstance.job_instance_id).correlate(JobInstance)
        sq_11 = sq_11.filter(Invocation.wf_id == Job.wf_id).correlate(Job)
        sq_11 = sq_11.filter(Invocation.task_submit_seq >= 0)
        sq_11 = sq_11.group_by().subquery()
        
        q = database.session.query (Job.job_id,
                                       JobInstance.job_instance_id,
                                       JobInstance.job_submit_seq,
                                       Job.exec_job_id.label('job_name'), JobInstance.site,
                                       cast(sq_1.as_scalar() - sq_2.as_scalar(), Float).label('condor_q_time'),
                                       cast(sq_3.as_scalar() - sq_4.as_scalar(), Float).label('resource_delay'),
                                       cast(JobInstance.local_duration, Float).label('runtime'),
                                       cast(Invocation.start_time, Float).label('start_time'),
                                       cast(sq_5.as_scalar(), Float).label('kickstart'),
                                       cast(sq_6.as_scalar() - sq_7.as_scalar(), Float).label('post_time'),
                                       cast(JobInstance.cluster_duration, Float).label('seqexec'),
                                       sq_8.as_scalar().label('exit_code'),
                                       sq_9.as_scalar().label('host_name'),
                                       JobInstance.multiplier_factor,
                                       cast(sq_10.as_scalar(), Float).label('kickstart_multi'),
                                       sq_11.as_scalar().label('remote_cpu_time'),
                                       cast(JobInstance.work_dir, String).label ('work_dir'),
                                       cast(JobInstance.sched_id, String).label ('sched_id'))
        q = q.filter(JobInstance.job_id == Job.job_id)
        q = q.filter(Job.wf_id.in_(database._wfs))
        q = q.order_by(JobInstance.job_submit_seq)
        
        return q.all ()

    def grok_subdax (self, database, dax_label, submit_dir, processor, since):
        max_timestamp = since
        workflow_states = database.get_workflow_states ()
        logger.debug ("(%s) workflow_states => %s", dax_label, json.dumps (workflow_states, cls = JobStatEncoder,indent=2))
        for state in workflow_states:
            if state.timestamp <= since:
                continue

            max_timestamp = state.timestamp
            event = None
            if state[1] == 'WORKFLOW_TERMINATED':
                event = JobStatistics ()
                event.exitcode = state [3]
            elif state[1] == 'WORKFLOW_STARTED':
                event = JobStatistics ()
            if event:

                if GraysonUtil.getPrecompiledPattern (self.ROOT_DIR_PAT, submit_dir) is not None:
                #if len (job_stats_list) < 2:
                    event.name = dax_label
                else:
                    #event.name = "subdax_%s" % os.path.basename (submit_dir) #wf_det.dax_label
                    event.name = os.path.basename (submit_dir) #wf_det.dax_label
                event.is_dax = True
                event.work_dir =  os.path.abspath (submit_dir)
                event.start_time = state [4]
                processor.processEvent (event)

        return max_timestamp

class EventScanner (object):

    DAX_START = "dax-start"
    DAX_END = "dax-end"

    def __init__(self, submit_dir):
        properties = os.path.join (submit_dir, "grayson.stampede.properties")
        properties = None
	self.db_url, self.wf_uuid = db_utils.get_db_url_wf_uuid (submit_dir, properties)
        logger.info ("db url: %s", self.db_url)
        logger.info ("wf id:  %s", self.wf_uuid)
        self.stampede = self.connect (self.wf_uuid)

    def connect (self, wf_uuid, expand = True):
        result = None
	try:
            result = StampedeStatistics (self.db_url, expand)
            result.initialize (wf_uuid)
        except SchemaVersionError:
            logger.error("------------------------------------------------------")
            logger.error("Database schema mismatch! Please run the upgrade tool")
            logger.error("to upgrade the database to the latest schema version.")
        except:
            logger.error("Failed to load the database." + self.db_url )
            logger.warning (traceback.format_exc ())
        return result

    def isDAXEvent (self, event):
        return event.is_dax

    def getJobStats (self, job): 
        job_retry_count_dict = {}  
        job_stats = JobStatistics ()
        job_stats.name = job.job_name
        job_stats.site = job.site
        job_stats.kickstart = job.kickstart
        job_stats.multiplier_factor = job.multiplier_factor
        job_stats.kickstart_mult = job.kickstart_multi
        job_stats.remote_cpu_time = job.remote_cpu_time
        job_stats.post = job.post_time
        job_stats.runtime = job.runtime
#        job_stats.start_time = job.start_time
        job_stats.condor_delay = job.condor_q_time
        job_stats.resource = job.resource_delay
        job_stats.seqexec = job.seqexec
        job_stats.exitcode = utils.raw_to_regular(job.exit_code)
        job_stats.hostname = job.host_name
        job_stats.sched_id = job.sched_id
        job_stats.work_dir = os.path.abspath (job.work_dir)
        job_stats.work_dir = job_stats.work_dir.replace ("work/outputs", "work")
        if job_stats.seqexec is not None and job_stats.kickstart is not None:
            job_stats.seqexec_delay = (float(job_stats.seqexec) - float(job_stats.kickstart))
        if job_retry_count_dict.has_key(job.job_name):
            job_retry_count_dict[job.job_name] += 1
        else:
            job_retry_count_dict[job.job_name] = 1
        job_stats.retry_count = job_retry_count_dict[job.job_name]
        return job_stats

    def accepts (self, job, nameFilter = None):
        accept = True
        if nameFilter:
            for prefix in nameFilter:
                if job.job_name:
                    if job.job_name.find (prefix) > -1:
                        accept = False
                        break
                else:
                    accept = False
                    break
        return accept

    def getEvents (self,
                   processor,
                   wf_uuid       = None,
                   daxFilter     = None,
                   jobNameFilter = [ 'clean_up',
                                     'chmod',
                                     'register_',
                                     'create_dir_' ],
                   since         = 0):

        if not wf_uuid:
            wf_uuid = self.wf_uuid
        max_timestamp = 0
        graysonStats = GraysonStampedeStatistics ()

        ''' connect '''
        database = self.connect (wf_uuid = wf_uuid, expand  = False)

        ''' is there anything new? '''
        max_time = graysonStats.get_max_timestamp (database)
        if max_time <= since:
            return since

        ''' get dax events for this workflow '''
        wf_det = database.get_workflow_details()[0]
        max_timestamp = max (graysonStats.grok_subdax (database   = database,
                                             dax_label  = wf_det.dax_label,
                                             submit_dir = wf_det.submit_dir,
                                             processor  = processor,
                                             since      = since),
                             max_timestamp)

        ''' read events '''
        max_timestamp = max (self.queryJobStats (graysonStats  = graysonStats,
                                       database      = database,
                                       wf_det        = wf_det,
                                       jobNameFilter = jobNameFilter,
                                       since         = since,
                                       processor     = processor),
                             max_timestamp)

        details = database.get_descendant_workflow_ids ()
        for wf_det in details:
            sub_wf_uuid  = wf_det.wf_uuid
            sub_database = self.connect (wf_uuid = sub_wf_uuid, expand = False)
            wf_det       = sub_database.get_workflow_details()[0]
            workflow_id  = str (sub_wf_uuid)
            dax_label    = str (wf_det.dax_label)
            logger.debug ("processing: %s, dax: %s, wfid: %s, dets: %s",
                         sub_wf_uuid,
                         dax_label,
                         workflow_id,
                         json.dumps (wf_det, indent=2, sort_keys=True))

            ''' There's no filter or the filter matches this dax '''
            logger.debug ("dax_label => %s", dax_label)
            if not daxFilter or daxFilter and dax_label == daxFilter: 
                ''' recurse - get events pertaining to the subdax '''
                max_timestamp = max (self.getEvents (processor     = processor,
                                           wf_uuid       = sub_wf_uuid,
                                           daxFilter     = daxFilter,
                                           jobNameFilter = jobNameFilter,
                                           since         = since),
                                     max_timestamp)
        return max_timestamp

    def queryJobStats (self, graysonStats, database, wf_det, jobNameFilter, since, processor):
        max_timestamp = graysonStats.get_max_timestamp (database)
        if max_timestamp > since:
            logger.debug ("max_timestamp: %s > %s : since", max_timestamp, since)
            wf_job_stats_list = graysonStats.get_job_statistics (database) # all events for one dax
            for job in wf_job_stats_list:
                if self.accepts (job = job, nameFilter = jobNameFilter):                        
                    job_stats = self.getJobStats (job)
                    processor.processEvent (job_stats)
                    logger.debug ("dax=%s, name=%s start=%s exit=%s host=%s sched=%s, rmcpu=%s, rntm=%s", 
                                  wf_det.dax_label,
                                  job_stats.name,
                                  job_stats.start_time,
                                  job_stats.exitcode,
                                  job_stats.hostname,
                                  job_stats.sched_id,
                                  job_stats.remote_cpu_time,
                                  job_stats.runtime)
        return max_timestamp

    def emitJSON (self, obj):
        return json.dumps (obj,
                           cls       = JobStatEncoder,
                           indent    = 2,
                           sort_keys = True)

class Processor (object):
    def processEvent (self, event):
        pass
    def acceptsEvent (self, event):
        return True

class BufferProcessor (Processor):
    def __init__(self):
        self.buffer = []
    def processEvent (self, event):
        self.buffer.append (event)

class DebugProcessor (Processor):            
    def processEvent (self, event):
        logger.debug ("event=>(%s)", json.dumps (event,
                                                 cls       = JobStatEncoder,
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
    max_timestamp = scanner.getEvents (wf_uuid   = scanner.wf_uuid,
                                       daxFilter = daxFilter,
                                       since     = since,
                                       processor = DebugProcessor ())
    logger.debug ("max_timestamp=%s", max_timestamp)

    '''
    text = scanner.emitJSON (eventBuffer)
    logger.debug ("output=>%s, max_timestamp=%s", text, max_timestamp)
    '''

