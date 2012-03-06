# -*- coding: utf-8 -*-

''' system '''
from string import Template
from copy import copy
import getopt
import json
import logging
import logging.handlers
import os
import re
import shlex
import shutil
import string
import socket
import subprocess
import sys
import time
import traceback
import glob
from sys import settrace

# third-party 
from Pegasus.DAX3 import ADAG
from Pegasus.DAX3 import DAX
from Pegasus.DAX3 import Executable
from Pegasus.DAX3 import File
from Pegasus.DAX3 import Job
from Pegasus.DAX3 import Link
from Pegasus.DAX3 import PFN
from Pegasus.DAX3 import Profile
from Pegasus.DAX3 import Transformation

# local #
from grayson.compiler.abstractsyntax import ASTProfile
from grayson.executor import Executor
from grayson.log import LogManager
from grayson.common.util import GraysonUtil
from grayson.wms.workflowManagementSystem import WorkflowManagementSystem
from grayson.wms.workflowManagementSystem import WorkflowModel

logger = logging.getLogger (__name__)

''' A plugin for the Pegasus WMS. '''
class PegasusWMS (WorkflowManagementSystem):
    def __init__(self):
        self.outputDir = os.getcwd ()
        self.pegasusProperties = PegasusProperties ()
        self.siteCatalog = SiteCatalogXML (self)
        self.transformationCatalog = PegasusTC ()
        self.replicaCatalog = PegasusFileRC ()
    def setOutputDir (self, outputDir):
        self.outputDir = outputDir
    def getOutputDir (self):
        return self.outputDir
    def getSiteCatalog (self):
        return self.siteCatalog
    def getTransformationCatalog (self):
        return self.transformationCatalog
    def getReplicaCatalog (self):
        return self.replicaCatalog
    def createWorkflowModel (self, namespace):
        return PegasusWorkflowModel (namespace)
    def enableShellExecution (self, enabled=True):
        return self.pegasusProperties.enableShellExecution (enabled)
    def enableSymlinkTransfers (self, enabled=True):
        self.pegasusProperties.enableSymlinkTransfers (enabled)

    ''' Get Pegasus specific arguments '''
    def getExecuteArguments (self, sites, workflow=None, other=[]):
        result = None

        pegasusHome = GraysonUtil.getPegasusHome ()
        args = ["-Dpegasus.user.properties=${outputDir}/${pegasusProperties}",
                "--sites ${sites}",
                "--force",
                "--verbose",
                "--verbose",
                "--verbose",
                "--output local"]
        if pegasusHome.find ("3.1") > -1 or pegasusHome.find ("4.0") > -1: 
            args = ["--conf=${outputDir}/${pegasusProperties}",
                    "--sites ${sites}",
                    "--dir ${outputDir}/work",
                    "--force",
                    "--verbose",
                    "--verbose",
                    "--verbose",
                    "--output local"]

        for arg in other:
            args.append (arg)
        template = Template (" ".join (args))
        context = {
            "outputDir"         : self.getOutputDir (),
            "pegasusProperties" : PegasusProperties.PEGASUS_PROPERTIES,
            "sites"             : sites
            }
        if workflow:
            context ["outputDax"] = os.path.join (self.getOutputDir (), workflow)
        result = template.substitute (context)
        logger.debug ("generated workflow execute arguments: %s", result) 
        return result

    ''' Execute workflow the Pegasus way. '''
    def executeWorkflow (self, sites, workflowName, compilerPlugin=None):
        additionalArgs = [ " --dax ${outputDax} --submit" ]
        additionalArgs = [ " --dir ${outputDir}/work --dax ${outputDax} --submit" ]
        arguments = self.getExecuteArguments (sites=sites,
                                              workflow=workflowName,
                                              other=additionalArgs)
        executeCommand = "pegasus-plan %s" % arguments
        logger.debug ("getExecuteArguments: %s", executeCommand)
        executor = Executor ({})
        logger.info ("--(pegasus-plan): %s", executeCommand)

        lines = []
        def submitProcessor (line):
            line = line.replace ("\n", "")
            lines.append (line)
            logger.info ("--(pegasus-plan): %s", line)

        wrappedOutputProcessor = submitProcessor
        if compilerPlugin:
            def wrappedOutputProcessor (line):
                submitProcessor (line)
                compilerPlugin.notifyShellEvent (line, workflowName)
        try:
            executor.execute (executeCommand, pipe=True, processor=wrappedOutputProcessor)
        except Exception as e:
            traceback.print_exc (e)
            ''' missing stderr. '''
            logger.error ('\n'.join (lines))
            raise e

    ''' Write Pegasus meta data catalogs. '''
    def writeMetaDataCatalogs (self):
        GraysonUtil.writeFile (
            outputPath=os.path.join (self.outputDir, PegasusProperties.SITE_CATALOG),
            data=self.getSiteCatalog().generateXML ())
        
        ''' replica catalog '''
        GraysonUtil.writeFile (
            outputPath=os.path.join (self.outputDir, PegasusProperties.REPLICA_CATALOG),
            data=self.getReplicaCatalog().generateRC ())
        
        ''' transformation catalog '''
        GraysonUtil.writeFile (
            outputPath=os.path.join (self.outputDir, PegasusProperties.TRANSFORMATION_CATALOG),
            data=self.getTransformationCatalog().generateTC ())
        
        ''' properties '''
        GraysonUtil.writeFile (
            outputPath=os.path.join (os.path.join (self.outputDir, PegasusProperties.PEGASUS_PROPERTIES)),
            data=self.pegasusProperties.generateProperties (configDir=self.outputDir))

''' Pegasus properties '''
class PegasusProperties:

    PEGASUS_PROPERTIES="pegasus.properties"
    REPLICA_CATALOG="replica-catalog.rc"
    SITE_CATALOG="sites.xml"
    TRANSFORMATION_CATALOG="transformation-catalog.tc"
    
    def __init__(self):
        self.symlinkTransfers = False
        self.text = """
pegasus.catalog.site=XML3
pegasus.catalog.site.file=${configDir}/${siteCatalog}

pegasus.catalog.replica=File
pegasus.catalog.replica.file=${configDir}/${replicaCatalog}

pegasus.catalog.transformation=File
pegasus.catalog.transformation.file=${configDir}/${transformationCatalog}

pegasus.dir.useTimestamp=true
pegasus.dir.storage.deep=false
pegasus.transfer.links=${symlinkTransfers}

pegasus.transfer.*.remote.sites=NERSC-Carver

${pegasusCodeGenerator}
"""
        self.pegasusCodeGenerator = ""

    def enableSymlinkTransfers (self, enabled=True):
        self.symlinkTransfers = enabled
        
    def enableShellExecution (self, enabled=True):
        self.pegasusCodeGenerator="pegasus.code.generator = Shell"

    def generateProperties (self, siteFile="sites.xml", configDir="."):

        '''
        generic way to pass pegasus properties

        remoteSites = []
        eachSite = sites.split (',')
        for site in eachSite:
            if not site == 'local':
                remoteSites.append (site)
        remoteSiteText = ','.join (remoteSites)

        pegasus.transfer.*.remote.sites=${remoteSites} 
        '''

        template = Template (self.text)
        context = {
            "configDir"             : configDir,
            "siteCatalog"           : self.SITE_CATALOG,
            "replicaCatalog"        : self.REPLICA_CATALOG,
            "transformationCatalog" : self.TRANSFORMATION_CATALOG,
            "symlinkTransfers"      : str(self.symlinkTransfers).lower (),
            "pegasusCodeGenerator"  : self.pegasusCodeGenerator 
            }
        return template.substitute (context)

''' Emit a pegasus transformation catalog '''
class PegasusTC:

    def __init__(self):
        '''Firefly        pegasus::kickstart                /panfs/panasas/CMS/app/engage/rynge/pegasus/3.0.0cvs/bin/kickstart                     INSTALLED   INTEL32::LINUX'''
        self.text = "${cluster}        ${namespace}::${jobName}                ${location}             ${transfer}   ${architecture}::${OS}"
        self.entries = []
        
    def addEntry (self,
                  jobName,
                  location,
                  transfer="INSTALLED",
                  architecture="INTEL64",
                  OS="LINUX",
                  cluster="local",
                  namespace="app"):
        if cluster == None:
            cluster = "local"
        if location.startswith (os.sep):
            location = "file://%s" % location
        
        if not transfer:
            transfer = "STAGEABLE"

        logger.debug ("wms:pegasus:transformationcatalog:add-entry : job=%s, location=%s, transfer=%s, arch=%s, os=%s, cluster=%s, namespace=%s",
                       jobName,
                       location,
                       transfer,
                       architecture,
                       OS,
                       cluster,
                       namespace)
        template = Template (self.text)
        context = {
            "jobName"               : jobName,
            "location"              : location,
            "transfer"              : transfer,
            "architecture"          : architecture,
            "OS"                    : OS,
            "cluster"               : cluster,
            "namespace"             : namespace
            }
        entryText = template.substitute (context)
        self.entries.append (entryText)
        
    def generateTC (self):
        return "\n".join (self.entries)

''' Write a pegasus file replica catalog '''
class PegasusFileRC (object):

    def __init__(self):
        self.text = '${fileName} ${fileURL} pool="${poolName}"'
        self.entries = {}
        
    def addEntry (self, fileName, fileURL, pool):
        if not fileURL is None:
            logger.debug ("wms:pegasus:replica-catalog:add-entry: file(%s)=>(%s,%s)", fileName, fileURL, pool)
            template = Template (self.text)
            context = {
                "fileName"  : fileName,
                "fileURL"   : fileURL,
                "poolName"  : pool
                }
            entryText = template.substitute (context)
            self.entries [fileName] = entryText
        
    def generateRC (self):
        values = []
        for key in self.entries:
            values.append (self.entries [key])
        values.sort ()
        return "\n".join (values)

''' Emit pegasus site catalog. '''
class SiteCatalogXML(object):

    LOCAL = "local"
    HOSTNAME = "hostName"

    def __init__(self, wms):
        self.wms = wms;
        self.sites = {}
        self.siteProperties = {
            "siteName"      : "local",
            "hostName"      : "localhost",
            "architecture"  : "x86_64",
            "os"            : "LINUX",
            "gridType"      : "gt2",
            "scheduler"     : "fork",
            "schedulerType" : "Fork",
            "jobType"       : "compute",
            "scratchFileServerProtocol"           : "file",
            "scratchFileServerURL"                : "file://",
            "scratchFileServerMountPoint"         : "",
            "scratchInternalMountPoint"           : "",
            "scratchInternalMountPointFreeSize"   : "100G",
            "scratchInternalTotalSize"            : "30G",
            "storageFileServerProtocol"   : "file",
            "storageFileServerMountPoint" : "",
            "storageMountPoint"           : "",
            "storageFreeSize"             : "100G",
            "storageTotalSize"            : "30G",
            "storageInternalMountPoint"   : "",
            "storageFreeSize"             : "100G",
            "storageTotalSize"            : "30G",
            "pegasusLocation"             : "/opt/pegasus",
            "globusLocation"              : "/opt/globus",
        }
        self.configureLocal ()

        self.xmlHeader = """<?xml version="1.0" encoding="UTF-8"?>
<sitecatalog
        xmlns="http://pegasus.isi.edu/schema/sitecatalog"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:schemaLocation="http://pegasus.isi.edu/schema/sitecatalog http://pegasus.isi.edu/schema/sc-3.0.xsd"
        version="3.0">
        """

        self.xmlSite ="""    
   <site  handle="${siteName}" arch="${architecture}" os="${os}">
      <grid  type="${gridType}" contact="${hostName}/jobmanager-fork" scheduler="Fork" jobtype="auxillary"/>
      <grid  type="${gridType}" contact="${hostName}/jobmanager-${scheduler}" scheduler="${schedulerType}" jobtype="${jobType}"/>
      <head-fs>
         <scratch>
            <shared>
               <file-server protocol="${scratchFileServerProtocol}" url="${scratchFileServerURL}" mount-point="${scratchFileServerMountPoint}"/>
               <internal-mount-point mount-point="${scratchInternalMountPoint}"/>
            </shared>
         </scratch>
         <storage>
            <shared>
               <file-server protocol="${storageFileServerProtocol}" url="${storageFileServerURL}" mount-point="${storageFileServerMountPoint}"/>
               <internal-mount-point mount-point="${storageInternalMountPoint}"/>
            </shared>
         </storage>
       </head-fs>
       <replica-catalog  type="LRC" url="rlsn://dummyValue.url.edu" />
       <profile namespace="env" key="PEGASUS_HOME" >${pegasusLocation}</profile>
       ${X509_user_proxy_profile}
       <profile namespace="env" key="GLOBUS_LOCATION" >${globusLocation}</profile>
   </site>"""

        self.xmlFooter="""
</sitecatalog>
        """

    def configureLocal (self):
        pegasusLocation = GraysonUtil.getPegasusHome ()

        globusLocation = os.getenv ("GLOBUS_LOCATION")
        if not globusLocation:
            raise ValueError ("GLOBUS_LOCATION must be defined")

        self.addEntry (
            "local",
            {
            "architecture"                : "x86",            # TODO: inspect environment
            "scratchFileServerProtocol"   : "file",
            "scratchFileServerMountPoint" : "%s/work/outputs" % self.wms.getOutputDir (),
            "scratchInternalMountPoint"   : "%s/work/outputs" % self.wms.getOutputDir (),
            "storageFileServerProtocol"   : "file",
            "storageFileServerMountPoint" : "%s/work/outputs" % self.wms.getOutputDir (),
            "storageMountPoint"           : "%s/work/outputs" % self.wms.getOutputDir (),
            "storageInternalMountPoint"   : "%s/work/outputs" % self.wms.getOutputDir (),
            "pegasusLocation"             : pegasusLocation,
            "globusLocation"              : globusLocation 
            })
        

    ''' Add a site catalog entry '''
    def addEntry (self, siteName, properties):
        if not siteName in self.sites:
            base = copy (self.siteProperties)        
            logger.debug ("wms:pegasus:register-site %s", base)
            base.update (properties)
            self.sites [siteName] = base

    ''' Get an entry '''
    def getEntry (self, siteName):
        return self.sites [siteName]
    
    def getScratchURL (self, fileName, siteKey="local"):
        return self.getURL (fileName, siteKey, urlType="scratch")

    ''' Get a site specific URL for storage or scratch space on a site '''
    def getURL (self, fileName, siteKey="local", urlType="storage"):
        fileURL = None
        protocolKey = "%sFileServerProtocol" % urlType
        mountPointKey = "%sFileServerMountPoint" % urlType
        if logging.getLogger().isEnabledFor (logging.DEBUG):
            logger.debug ("getURL(%s, %s, %s) protocolKey: %s, mountPointKey: %s",
                           fileName,
                           siteKey,
                           urlType,
                           protocolKey,
                           mountPointKey)
        if siteKey in self.sites:
            logger.debug ("siteinsites %s", siteKey)

            site = self.getEntry (siteKey)
            if protocolKey in site and mountPointKey in site:
                hostname = site ["hostName"]
                protocol = site [protocolKey]
                mountPoint = site [mountPointKey]
                if protocol == "file":            
                    fileURL = "file://%s/%s" % (mountPoint, fileName)
                else:
                    if self.HOSTNAME in site:
                        hostname = site [self.HOSTNAME]
                        fileURL = "%s://%s/%s/%s" % (protocol, hostname, mountPoint, fileName)
                logger.debug ("getURL (url=%s hostname=%s, protocol=%s, mountPoint=%s\nsite=%s)",
                               fileURL,
                               hostname,
                               protocol,
                               mountPoint,
                               site)
        return fileURL
    
    def generateXML (self):
        siteText = [self.xmlHeader]
        for siteName in self.sites:
            logger.debug ("generating site catalog data for site (%s)", siteName)
            site = self.sites [siteName]


            x509userproxyKey = 'x509userproxy'
            x509userproxyProfileKey = 'X509_user_proxy_profile'
            x509userproxyProfile = ''
            if x509userproxyKey in site:
                x509userproxyProfile = '<profile namespace="condor" key="x509userproxy" >%s</profile>' % site [x509userproxyKey]
            site [x509userproxyProfileKey] = x509userproxyProfile

            for kind in [ 'scratch', 'storage' ]:
                fileServerProtocolKey = "%sFileServerProtocol" % kind
                fileServerURLKey = "%sFileServerURL" % kind
                if site [fileServerProtocolKey] is "file":
                    site [fileServerURLKey] = "file://"
                else:
                    site [fileServerURLKey] = "%s://%s" % (site [fileServerProtocolKey], site ["hostName"])
            template = Template (self.xmlSite)
            siteText.append (template.substitute (site))
        siteText.append (self.xmlFooter)
        return "\n".join (siteText)

''' A Pegasus specific representation of a workflow.
    Wraps the Pegasus DAX API and ADAG in particular. '''
class PegasusWorkflowModel (WorkflowModel):
    
    def __init__(self, namespace):
        logger.debug ("wms:pegasus:create-workflowmodel: %s" % namespace)
        self.adag = ADAG (namespace)
        self.namespace = namespace
        self.files = {}
        self.exes = {}
        self.propertyMap = {}
        self.nodes = {}
        self.workflowRoot = os.getcwd ()

        self.jobTransformations = {}
        
    def setWorkflowRoot (self, workflowRoot):
        self.workflowRoot = workflowRoot

    def setProperties (self, nodeId, properties):
        logger.debug ("wms:pegasus:dax:setprops: (%s)->(%s)" % (nodeId, properties))
        self.propertyMap [nodeId] = properties
        
    def getProperties (self, nodeId):
        return self.propertyMap [nodeId]
    
    def createFile (self, fileName):
        return File (fileName)
    
    def addNode (self, id, node):
        logger.debug ("wms:pegasus:dax:add-node: (%s)->(%s)" % (node.getId(), properties))
        self.nodes [id] = node

    def getNode (self, id):
        node = None
        if id in self.nodes:
            node = self.nodes [id]
            return node
        
    def addFile (self, fileName, fileURL=None, site=None):
        file = self.getFile (fileName)
        if not file:            
            file = File (fileName)
            if not fileURL:
                fileURL = "file://%s/%s" % (self.workflowRoot, fileName)
            if not site:
                site = "local"
 
            logger.debug ("--add-pfn: (%s)(%s)(%s)", fileName, fileURL, site)
            pfn = PFN (fileURL, site)
            file.addPFN (pfn)
            self.adag.addFile (file)
            self.files [fileName] = file
        return file
	
    def getFile (self, fileName, prefix=""):
        key = "%s%s" % (prefix, fileName)
        if key in self.files:
            logger.debug ("wms:pegasus:dax:get-file: (%s)" % key)
            return self.files [key]
        else:
            return None
	
    def addExecutable (self, jobId, name, path, version="4.0", exe_os="linux", exe_arch="x86", site="local", installed="true"):
        e_exe = self.getExecutable (name)
        if not e_exe:
            e_exe = Executable (
                namespace=self.namespace, 
                name=name, 
                version=version, 
                os=exe_os, 
                arch=exe_arch, 
                installed=installed)
            if not site:
                site = "local"
            if not installed:
                installed = False
            if logging.getLogger().isEnabledFor (logging.DEBUG):
                logger.debug ("wms:pegasus:dax:add-exe: (name=[%s], path=[%s], version=[%s], os=[%s], arch=[%s], site=[%s], installed=[%s])" % 
                               (name,
                                path,
                                version,
                                exe_os,
                                exe_arch,
                                site,
                                installed))
            if not "://" in path:
                path = "file://%s" % path
            if not path:
                raise ValueError ("empty path for executable: %s at site %s" % (name, site))

            e_exe.addPFN (PFN (path, site))
            if not installed:
                e_exe.installed = installed
            self.adag.addExecutable (e_exe)
            self.exes [name] = e_exe

            transformation = Transformation (name, self.namespace, version)
            self.jobTransformations [jobId] = transformation
            
        return e_exe
    
    def getExecutable (self, name):
        key = name
        if key in self.exes:
            return self.exes [key]
        else:
            return None

    def addSubWorkflow (self, name, transformation=None):
        #self.adag.addTransformation (transformation)
        abstractJob = DAX (name)
        self.adag.addDAX (abstractJob)
        return abstractJob
    
    def addJob (self, id):
        #self.adag.addTransformation (transformation)
        transformation = self.jobTransformations [id]
        logger.debug ("wms:pegasus:add-job: transformation(%s) jobid(%s)", transformation.name, id)
        abstractJob = Job (name=transformation, id=id)
        self.adag.addJob (abstractJob)
        return abstractJob
    
    def addProfiles (self, abstractJob, profiles):
        if profiles:
            for astProfile in profiles:
                logger.debug ("wms:pegasus:add-profile: (namespace=%s,key=%s,value=%s) to job (%s)",
                               astProfile.namespace,
                               astProfile.key,
                               astProfile.value,
                               abstractJob.name)
                profile = Profile (astProfile.namespace,
                                   astProfile.key,
                                   astProfile.value)
                abstractJob.addProfile (profile)

    def addFiles (self, abstractJob, files, link):
        if files:
            for fileKey in files:
                tuple = files [fileKey]
                fileElement = tuple [0]
                file = fileElement.getDaxNode ()
                abstractJob.uses (file, link=link)
                arg = tuple [1]
                if arg:
                    abstractJob.addArguments (arg, file)

    def addInputFiles (self, abstractJob, files):
        self.addFiles (abstractJob, files, Link.INPUT)

    def addOutputFiles (self, abstractJob, files):
        self.addFiles (abstractJob, files, Link.OUTPUT)

    def addArguments (self, abstractJob, arguments):
        if arguments:
            abstractJob.addArguments (arguments)

    def addDependency (self, parent, child):
        self.adag.addDependency (parent, child)
                        
    def writeExecutable (self, stream):
        self.adag.writeXML (stream)

    def getADAG (self):
        return self.adag
