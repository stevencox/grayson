# -*- coding: utf-8 -*-
 
''' system '''
import getopt
import glob
import json
import logging
import os
import re
import shlex
import shutil
import socket
import string
import subprocess
import sys
import time
import traceback
from copy import copy
from string import Template
from sys import settrace

''' local '''
from grayson.compiler.abstractsyntax import ASTElement
from grayson.compiler.exception import GraysonCompilerException
from grayson.compiler.exception import CycleException
from grayson.compiler.cycle import CycleDetector
from grayson.executor import Executor


from grayson.graphml import Edge
from grayson.graphml import Graph
from grayson.graphml import GraphMLParser
from grayson.graphml import Node
'''
from grayson.jsonparser import Edge
from grayson.jsonparser import Graph
from grayson.jsonparser import JSONParser
from grayson.jsonparser import Node
'''

from grayson.log import LogManager
from grayson.packager import GraysonPackager
from grayson.common.util import GraysonUtil
from grayson.wms.pegasus.pegasusWMS import PegasusWMS
from grayson.wms.workflowManagementSystem import WorkflowManagementSystem

logger = logging.getLogger (__name__)

class Operator (object):
    
    DYNAMIC_INDEX = "dynIndex"    

    def _isDynamicOperator (properties):
        return properties and Operator.DYNAMIC_INDEX in properties

    @staticmethod
    def isDynamicOperator (compiler):
        #ninja
        logger.debug ("compiler id: %s isdynamic %s", compiler.compilerId, compiler.compilerContext.isDynamicOperator)
        return compiler and compiler.compilerContext.isDynamicOperator

    @staticmethod
    def getDynamicIndex (properties):
        return properties [Operator.DYNAMIC_INDEX] if Operator.DYNAMIC_INDEX in properties else None

class CompilerPlugin (object):
    """ Defines the API for a compiler plugin."""

    def notifyShellEvent (self, line, outputWorkflowPath):
        """ Notify the plugin that a line was emitted by the programs execution. """
        pass
    def notifyWorkflowCreation (self, workflowGraph, outputWorkflowPath, topWorkflow):
        """ Notify the plugin of a workflow creation event. """
        pass

class ASTContext:
    """ Context object modeling the state of an abstract syntax tree during compilation. """
    def __init__(self):
        self.dependencies = {}
        self.wmsjobs = {}
    def addWmsJob (self, id, job):
        self.wmsjobs [id] = job
    def getWmsJobs (self):
        return self.wmsjobs
    def getWmsJob (self, id):
        value = None
        if id in self.wmsjobs:
            value = self.wmsjobs [id]
        return value
    def setDependencies (self, id, dependencies):
        self.dependencies[id] = dependencies
    def getDependencies (self, id):
        value = None
        if id in self.dependencies:
            value = self.dependencies [id]
        return value

class JobContext:
    """ Context object to model the state of a job during compilation. """
    def __init__(self, job, namespace, version):
        self.job = job
        self.origins = []
        self.inputFiles = []
        self.outputFiles = []
        self.inFiles = {}
        self.outFiles = {}
    def getJob (self):
        return self.job
    def addOrigin (self, origin):
        logger.debug ("job context add origin: origin(%s) job(%s, %s)", origin, self.job.getId (), self.job.getLabel ())
        if origin == self.job.getId ():
            logger.debug ("maybe-bad: %s shows itself as the source of one of its own input files. Hopefully this is an aspect.", self.job.getLabel ()) 
        else:
            if not origin in self.origins:
                self.origins.append (origin)
    def getOrigins (self):
        return self.origins
    
class CompilerContext (object):
    """ Models compiler properties which are shared across recursive invocations. """
    def __init__(self, outputDir):
        self.topModel = None
        self.properties = ASTElement (Node ("x", "{}", ""))
        self.localFileLocations = {}
        self.aspects = []
        self.sites = "local"
        self.workflowManagementSystem = PegasusWMS (outputDir)
        self.processedWorkflows = []
        self.inputModelProperties = {}
        self.allModelPaths = []
        self.packaging = False
        self.compilerPlugin = CompilerPlugin ()

        self.appliedAspects = {}
        self.seenPointcuts = {}
        self.syntheticIds = {}

        self.generatedFile = {}

        self.isDynamicOperator = False

    def getWorkflowManagementSystem (self):
        return self.workflowManagementSystem
    
class GraysonCompiler:
    """Read a graph structure and convert to semantics suitable for execution via a grid workflow management system."""

    SYNTHETIC_ID = 0
    LAMBDA_ID = 0

    def __init__(self, namespace, version, logManager, outputDir, clean=False, appHome=None):
        self.ABSTRACT = "abstract"
        self.GRAYSON_HOME = "graysonHome"
        self.GRAYSON_VAR = "graysonVar"
        self.APP_HOME = unicode ("appHome")
        self.OUTPUT_DIR = unicode ("outputDir")
        self.FQDN = "FQDN"
        self.ASPECT  = "aspect"
        self.ATTR_ARCHITECTURE  = "arch"
        self.ATTR_ARG  = "arg"
        self.ATTR_ARGS  = "args"
        self.ATTR_INSTALLED = "installed"
        self.ATTR_LOCAL = "local"
        self.ATTR_PATH = "path"
        self.ATTR_REFERENCE  = "reference"
        self.ATTR_SITE = "site"
        self.ATTR_TYPE = "type"
        self.ATTR_VERSION  = "version"
        self.EXECUTABLE = "executable"
        self.FILE = "file"
        self.GRAYSON_FILE_ARG = "grayson.file.arg"
        self.GRAYSONPATH = "GRAYSONPATH"
        self.GRAYSON_REDIRECT_OUTPUT_TO = "grayson.redirect.output.to"
        self.INPUT = "in"
        self.JOB = "job"
        self.OUTPUT = "out"
        self.PROPERTIES = "properties"
        self.WORKFLOW = "workflow"
        self.DAX = "dax"
        self.MAP = "map"

        self.CONTEXT_MODEL = "context"
        self.MODEL_SUFFIX = "graphml"
        self.CONTEXT_MODEL_TAG = "-context.graphml"
        '''
        self.MODEL_SUFFIX = "json"
        self.CONTEXT_MODEL_TAG = "-context.json"
        '''
        
        self.EXECUTION_MODE = "execution-mode"
        self.EXECUTION_MODE__SHELL = "shell"
        self.DATA_CONFIGURATION = "data-configuration"
        self.CONF_INPUT_PROPERTIES = "define"
        self.CONF_OUTPUT_FILE = "output-file"
        self.CONF_SITES = "sites"
        self.CONF_FILE = "grayson.conf"

        self.ASPECT_POINTCUT = "pointcut"
        self.ASPECT_AFTER = "after"
        self.ASPECT_BEFORE = "before"
        self.ASPECT_FROM = "from"
        self.ASPECT_TO = "to"
        self.VARIABLE = "variable"
        self.PATTERN = "pattern"

        self.MAP__STYLE = "style"
        self.MAP__EACH = "each"
        self.MAP__STYLE_CHAIN = "chain"
        self.MAP__STYLE_DYNAMIC = "dynamic"

        self.START = "start"
        self.END = "end"
        
        self.SYMLINK_TRANSFER = "symlink"
        self.URL_PREFIX = "urlPrefix"
        
        self.compilerId = ""
        self.namespace=namespace
        self.version=version
        self.logManager = logManager

        self.output = None
        self.graph = None
        self.workflowCompiler = {}
        self.astElements = {}
        self.typeIndex = {}
        self.labelIndex = {}
        self.referenceIndex = {}
        self.validModel = True
        self.errorMessages = []
        
        self.appliedAspects = {}


        self.clean = clean       # Delete previous artifacts and tests
        self.appHome = appHome   # Home directory of the application
        self.roots = []          # Jobs that dont depend on other jobs
        self.contextModels = []  # Models that provide context (are not workflows)

        self.compilerContext = CompilerContext (outputDir)
        self.workflowModel = self.compilerContext.getWorkflowManagementSystem().createWorkflowModel (self.namespace)
         
        path = os.getenv (self.GRAYSONPATH)
        logger.debug ("compiler:init:modelpath: pathvar: %s: path: %s separator: %s", self.GRAYSONPATH, path, os.pathsep)
        if path:
            self.compilerContext.modelPath = path.rsplit (os.pathsep)
        else:
            self.compilerContext.modelPath = [ ".", "model" ]

        for element in self.compilerContext.modelPath:
            logger.debug ("compiler:init:pathelement: %s", element)

    #////////////////////////////////////////////////////////////
    #{ 1.0 Compiler Context Access
    #////////////////////////////////////////////////////////////


    def ctx (self):
        return self.compilerContext

    def setCompilerPlugin (self, compilerPlugin):
        """ Configure a plugin for the compiler instance."""
        self.compilerContext.compilerPlugin = compilerPlugin
    def getCompilerPlugin (self):
        """ Get the configured compiler plugin."""
        return self.compilerContext.compilerPlugin

    def setPackaging (self, packaging=False):
        """ Assert that this execution is creating a portable model archive. """
        self.compilerContext.packaging = packaging

    def isPackaging (self):
        """ Test if this execution is creating a model archive."""
        return self.compilerContext.packaging

    def setTopModel (self, topModel):
        """ Assert that topModel is the root of a tree of graphs. """
        self.compilerContext.topModel = topModel

    def getTopModel (self):
        """ Return the root of the tree of graphs. """
        return self.compilerContext.topModel
    
    def isTopModel (self):
        """ Test if this compiler is processing the top model as opposed to a subworkflow or context model. """
        return self.compilerContext.topModel == self.compilerId
    
    def isContextModel (self, model=None):
        """ Test if model is a context model. """
        if not model:
            model = self.compilerId
        isContext = self.CONTEXT_MODEL_TAG in model
        logger.debug ("is-context-model: %s -> %s", model, isContext)
        return isContext
    
    def setSites (self, sites):
        self.compilerContext.sites = sites

    def getSites (self):
        useLocal = True
        if self.compilerContext.getWorkflowManagementSystem().getDataConfiguration ():
            useLocal = False
        value = []

        sites = self.compilerContext.sites.split (",")
        for site in sites:
            if site == "local":
                if useLocal:
                    value.append (site)
            else:
                value.append (site)

        return ",".join (value)
    
        #return self.compilerContext.sites

    def getTransformationCatalog (self):
        return self.compilerContext.getWorkflowManagementSystem().getTransformationCatalog ()

    def getReplicaCatalog (self):
        return self.compilerContext.getWorkflowManagementSystem().getReplicaCatalog ()
    
    def getSiteCatalog (self):
        return self.compilerContext.getWorkflowManagementSystem().getSiteCatalog ()

    def writeMetaDataCatalogs (self):
        self.compilerContext.getWorkflowManagementSystem().writeMetaDataCatalogs ()

    def getWorkflowManagementSystem (self):
        return self.compilerContext.getWorkflowManagementSystem()
    
    def setInputModelProperties (self, properties):
        self.compilerContext.inputModelProperties = properties

    def getInputModelProperties (self):
        return self.compilerContext.inputModelProperties

    def setModelPath (self, path):
        self.compilerContext.modelPath = path

    def getModelPath (self):
        return self.compilerContext.modelPath

    def getOutputDir (self):
        return self.compilerContext.getWorkflowManagementSystem().getOutputDir ()
    
    def getProperty (self, key):
        return self.compilerContext.properties.get (key)

    #////////////////////////////////////////////////////////////
    #{ 2.0 Abstract Model Manipulation
    #////////////////////////////////////////////////////////////

    def parse (self, models=[], graph=None):
        """ Parse each graph named in model. If graph is given, merge results of parsing into graph."""

        ''' order models '''
        final_models = []
        if models:
            for model in models:
                if model.endswith (self.CONTEXT_MODEL_TAG):
                    self.contextModels.append (model)
                else:
                    final_models.append (model)
            for model in models:
                if model.endswith (self.CONTEXT_MODEL_TAG):
                    final_models.append (model)

        if len (final_models) > 0:
            parser = GraphMLParser ()
            #parser = JSONParser ()
            self.compilerId = final_models [0]
            self.graph = parser.parseMultiple (final_models,
                                               path=self.compilerContext.modelPath,
                                               graph=graph)
        else:
            message = "Empty model list. Supply at least one model file."
            logger.error (message)
            raise ValueError (message)

        for path in self.graph.fileNames:
            if not path in self.compilerContext.allModelPaths:
                logger.debug ("add-model-path: %s", path)
                self.compilerContext.allModelPaths.append (path)

    def getAllModelPaths (self):
        return self.compilerContext.allModelPaths

    def addElement (self, id, element):
        """ Add an abstract syntax element to the AST. """
        if not isinstance (element, ASTElement):
            raise ValueError ("Accepts ASTElement only. Got: %s", element)
        elementType = element.get (self.ATTR_TYPE)
        self.astElements [id] = element
        if elementType:
            if not elementType in self.typeIndex:
                self.typeIndex[elementType] = []
            self.typeIndex [elementType].append (element)
            node = element.getNode ()
            if isinstance (node, Node):
                if elementType == self.ATTR_REFERENCE:
                    self.referenceIndex [node.getLabel ()] = element
                else:
                    self.labelIndex [node.getLabel ()] = element
                    logger.debug ("ast:add-elem:label-index: name=%s", element.getLabel ())
            logger.debug ("ast:add-elem:type-index: name=%s type=%s cid=(%s) type=(%s)",
                          element.getLabel (),
                          element.getType (),
                          self.compilerId,
                          elementType)

    def removeElement (self, id, removeEdges=True):
        """ Remove an abstract syntax element from the AST. """
        if id in self.astElements:
            element = self.astElements [id]
            if element:
                elementType = element.getType ()
                if elementType in self.typeIndex:
                    instances = self.typeIndex [elementType]
                    keep = []
                    for instance in instances:
                        if instance.getId () != id:
                            keep.append (instance)
                            logger.debug ("    remaining [%s] in typeIndex: %s", instance.getLabel (), elementType)
                        else:
                            logger.debug ("removing from typeIndex: %s type(%s)", element.getLabel (),elementType)
                    self.typeIndex [elementType] = keep
                label = element.getLabel ()
                if label in self.labelIndex:
                    del self.labelIndex [label]
                    logger.debug ("removing from labelIndex: %s", element.getLabel ())
            del self.astElements [id]
            logger.debug ("removing from astElements: %s", element.getLabel ())
        logger.debug ("removing from graph: %s", id)
        self.graph.removeNode (id)
        if removeEdges:
            edges = self.graph.getEdges ()
            for edge in edges:
                if edge.getTarget () == id or edge.getSource () == id:
                    self.graph.removeEdge (edge)
                    if edge.getId () in self.astElements:
                        del self.astElements [edge.getId ()]
                    logger.debug ("      removing edge: %s src:%s target:%s",
                                  id,
                                  edge.getSource(),
                                  edge.getTarget ())

    def getElementByLabel (self, label):
        """ Find an AST element by label. """
        value = None
        if label in self.labelIndex:
            value = self.labelIndex [label]
        return value
    
    def getReferenceByLabel (self, label):
        return self.referenceIndex [label] if label in self.referenceIndex else None

    def getElementsByType (self, kind):
        """ Get an AST element by type. """
        value = []
        if type(kind) == list:
            for k in kind:
                v = self.getElementsByType (k)
                for t in v:
                    value.append (t)
        elif kind in self.typeIndex:
            value = self.typeIndex [kind]

        return value

    def getElementKeys (self):
        """ Get keys of all elements. """
        return self.astElements.keyiter ()

    def getElementsById (self, ids, accept=None):
        """ Get a list of elements based on a list of ids. 
        If accept is specified, return only elements whose type is equal to accept. """
        result = []
        for id in ids:
            element = self.getElement (id)
            if element:
                if accept:
                    if element.getType () == accept:
                        result.append (element)
                else:
                    result.append (element)
        return result

    def getElementsByRegex (self, regex):
        values = []
        for key in self.labelIndex:
            if re.match (regex, key):
                values.append (self.labelIndex [key])
        return values

    def getElement (self, id, dereference=True, regex=False):
        """ Get an element. Dereference if necessary. """
        value = None
        if id in self.astElements:
            value = self.astElements [id]

        if dereference:
            value = self.dereference (value, regex)

        return value

    def dereference (self, original, regex=False):
        value = None
        if original:
            type = original.get (self.ATTR_TYPE)
            if not type == self.ATTR_REFERENCE:
                value = original
            else:

                if regex:
                    value = self.getElementsByRegex (original.getLabel ())
                else:
                    value = self.getElementByLabel (original.getLabel ())
                    if value:
                        logger.debug ("ast:dereference: (%s) to object (%s) of type (%s)",
                                      original.getLabel (),
                                      value.getLabel (),
                                      value.getType () )
                    else:
                        logger.debug ("        (reference-not-found) (%s)", original.getLabel ())
        return value

    def addError (self, message):
        logger.error (message)
        self.errorMessages.append (message)

    def reportErrors (self):
        for message in self.errorMessages:
            logger.error ("%s" % message)

    def failValidation (self, message):
        self.addError (message)
        self.validModel = False
        
    def validateGraph (self):
        """Validate the graph. Raise an error if a cycle is detected."""

        ''' get ids '''
        nodeKeys = list (set 
                         (map ( lambda x : x.getId (),
                                self.graph.getNodes ()) 
                          ))
        edgeKeys = list (set 
                         (map ( lambda edge : ( edge.getSource (),
                                                edge.getTarget () ),
                                self.graph.getEdges ()) 
                          ))

        ''' Aspects create cycles. Eliminate edges between generated nodes '''
        edgeFilter = []            
        for edge in edgeKeys:
            sourceKey, targetKey = edge
            source = self.getElement (sourceKey)
            target = self.getElement (targetKey)
            if source and target:
                tag = 'allowCycle'
                if not tag in source.getContext () and not tag in target.getContext ():
                    edgeFilter.append (edge)
        edgeKeys = edgeFilter

        ''' log '''
        if logger.isEnabledFor (logging.DEBUG):
            for k in nodeKeys:
                e = self.getElement (k)
                if e:
                    logger.debug (" nodes: %8s: [%-35s]", k, e.getLabel ())
            for k in edgeKeys:
                source = self.getElement (k [0])
                target = self.getElement (k [1])
                if source and target:
                    logger.debug (" edges: id(%8s->%10s) src(%8s: [%10s]) trg(%8s: [%10s])",
                                  k[0], k[1],
                                  source.getId (), source.getLabel (),
                                  target.getId (), target.getLabel ())

        ''' detect cycles '''
        cycleDetector = CycleDetector (nodes = nodeKeys, edges = edgeKeys)
        cycle = cycleDetector.detect_cycle ();
            
        if cycle:
            buffer = [ "Workflow models may not contain cycles.",
                       "The following nodes form a cycle:" ]
            for key in cycle:
                node = self.graph.getNode (key)
                if node:
                    buffer.append ("    node: key(%s) label(%s)" % (key, node.getLabel ()) )
            buffer.append ("Cycle detected in graph")
            raise CycleException ("\n".join (buffer))

    def validateModel (self):
        logger.debug ("validate-graph")
        for key in self.astElements.iterkeys ():
            element = self.getElement (key)
            if element:
                if element.get (self.ATTR_TYPE) == self.FILE:
                    fileName = element.getLabel ()
                    if not os.path.exists (fileName):
                        self.failValidation ("File: %s does not exist." % fileName)



    #////////////////////////////////////////////////////////////
    #{ 3.0 Workflow Construction
    #////////////////////////////////////////////////////////////

    def addExecutable (self, jobContext, source):
        """ Add an executable to a jobs context. """
        job = jobContext.getJob ()
        jobLabel = job.getNode().getLabel ()
        site = source.get (self.ATTR_SITE)
        path = source.get (self.ATTR_PATH)
        installed = source.get (self.ATTR_INSTALLED)
        architecture = source.get (self.ATTR_ARCHITECTURE)
        logger.debug ("ast:add-executable: job=%s", jobLabel)

        # default path to $appHome/bin/<nodeName>
        if not path:
            path = os.path.join (self.appHome, 'bin', source.getLabel ())

        path = os.path.normpath (path)

        urlPrefix = source.get (self.URL_PREFIX)
        if urlPrefix:
            path = "%s/%s" % (urlPrefix, source.getLabel ())

        if self.getWorkflowManagementSystem().isShellExecutionEnabled ():
            installed = "true"

        exe = self.workflowModel.addExecutable (jobId = job.getId (),
                                                name = jobLabel,
                                                path = path,
                                                version = self.version,
                                                site = site,
                                                exe_arch = architecture,
                                                installed = installed)
        self.getTransformationCatalog().addEntry (jobName   = jobLabel,
                                                  location  = path,
                                                  transfer  = "INSTALLED" if installed == "true" else None,
                                                  cluster   = site,
                                                  namespace = self.namespace,
                                                  version   = self.version)
        source.setDaxNode (exe)
        job.addProfiles (source)

    def getFileURL (self, fileElement, site=None):
        """ Get the URL for the given file element. Will use urlPrefix if the element has that property."""
        if not site:
            site = self.ATTR_LOCAL
            
        fileName = fileElement.getLabel ()
        fileURL = self.getSiteCatalog().getScratchURL (fileName, site)

        logger.debug ("--scratchurl: %s", fileURL)

        urlPrefix = fileElement.get (self.URL_PREFIX)
        if urlPrefix:
            fileURL = "%s/%s" % (urlPrefix, fileName)

        symlinkTransfer = fileElement.get (self.SYMLINK_TRANSFER)
        if symlinkTransfer == str(True).lower ():
            self.getWorkflowManagementSystem().enableSymlinkTransfers ()
            
        logger.debug ("fileURL: %s, urlPrefix %s", fileURL, urlPrefix)
        return fileURL
    
    def addOutputFile (self, jobContext, fileElement, edge):
        """ Add an output file to the job context. """
        job = jobContext.getJob ()
        fileName = fileElement.getNode().getLabel ()
        file = self.workflowModel.createFile (fileName)
        fileElement.setDaxNode (file)
        arg = edge.get (self.ATTR_ARG)
        logger.debug ("ast:add-output: arg=%s file=%s source=%s" % 
                      (arg,
                       fileName,
                       job.getNode().getLabel ()) )


        site = fileElement.get (self.ATTR_SITE)
        fileURL = self.getFileURL (fileElement, site),
        if not site:
            site = self.ATTR_LOCAL
        if site == self.ATTR_LOCAL:
            if fileName in self.compilerContext.localFileLocations:
                fileURL = self.compilerContext.localFileLocations [fileName]
        file = self.workflowModel.addFile (fileName, fileURL, site)
        fileElement.setDaxNode (file)

        jobContext.outFiles [fileElement.getLabel ()] = (fileElement, arg)        
        self.ctx().generatedFile [fileElement.getLabel ()] = True
        self.getReplicaCatalog().removeEntry (fileName)

    def addInputFile (self, jobContext, fileElement, edge):
        """ Add an input file to the job context. """
        job = jobContext.getJob ()
        fileName = fileElement.getLabel ()
        inputOrigins = fileElement.getOrigins (self.graph)
        for o in inputOrigins:
            logger.debug ("ast:origin: %s" % o)
            jobContext.addOrigin (o)
        arg = edge.get (self.ATTR_ARG)
        site = fileElement.get (self.ATTR_SITE)
        if not site:
            site = self.ATTR_LOCAL
        logger.debug ("ast:add-input: arg=%s file=%s job=%s site=%s", 
                      arg,
                      fileName,
                      job.getNode().getLabel (),
                      site)
        fileURL = self.getFileURL (fileElement, site),
        logger.debug ("get-file-url: %s", fileURL)
        if site == self.ATTR_LOCAL:
            if fileName in self.compilerContext.localFileLocations:
                fileURL = self.compilerContext.localFileLocations [fileName]
        file = self.workflowModel.addFile (fileName, fileURL, site)
        fileElement.setDaxNode (file)
        jobContext.inFiles [fileElement.getLabel ()] = (fileElement, arg)
        '''
                                           '''
        self.getReplicaCatalog().addEntry (fileName,
                                           self.getFileURL (fileElement, site),
                                           site)

        ''' Ensure we add only files that are inputs to the workflow rather
            than intermeidate (generated) files
        targetEdges = fileElement.getTargetEdges (self.graph)
        isWorkflowInput = not fileName in self.ctx().generatedFile
        if len (targetEdges) == 0 and isWorkflowInput:
            self.getReplicaCatalog().addEntry (fileName,
                                               self.getFileURL (fileElement, site),
                                               site)
                                               '''
    def formWorkflowName (self, element):
        return "%s.dax" % element.getLabel ()

    def getLogicalName (self, text):
        result = text
        match = re.search ('(.*)\.([0-9]+)', result)
        if match:
            result = match.group (1)
        return result
    
    def formWorkflowSourceName (self, element):
        result = self.getLogicalName (element.getLabel ())
        logger.debug ("ast:form-workflow-name: %s from element %s", result, element.getLabel ())
        return "%s.%s" % (result, self.MODEL_SUFFIX)

    #////////////////////////////////////////////////////////////
    #{ 4.0 Recursive Compilation
    #////////////////////////////////////////////////////////////
    def createComponentCompiler (self, elementName, version):
        """ Create a compiler object, promoting this compiler context. """
        logger.debug ("ast:compile-component: start(%s)" % elementName )
        compiler = GraysonCompiler (namespace  = elementName,
                                    version    = version,
                                    logManager = self.logManager,
                                    clean      = self.clean,
                                    appHome    = self.appHome,
                                    outputDir  = self.getOutputDir ())
        compiler.compilerContext = self.compilerContext
        return compiler

    def executeCompiler (self, compiler, elementName, outputFile):
        """ Execute the compiler semantic analysis and output. """
        compiler.buildAST ()
        if not self.isPackaging ():
            outputFileName = os.path.join (self.getOutputDir (), outputFile)
            output = open (os.path.join (self.getOutputDir (), outputFile), "w")
            compiler.writeDAX (output)
            output.close ()

            isTopWorkflow = self.output and outputFileName.endswith (self.output)
            self.getCompilerPlugin().notifyWorkflowCreation (self.getLogicalName (elementName),
                                                             outputFileName,
                                                             isTopWorkflow)
        outputDir = self.getOutputDir ()
        fileURL = "file://%s/%s" % (outputDir, outputFile)
        if outputDir == ".":
            fileURL = "file://%s/%s" % (os.getcwd (), outputFile)
        self.getReplicaCatalog().addEntry (outputFile, fileURL, "local") 
        logger.debug ("ast:compile-component:end: (%s)" % elementName )

    def ast_compileWorkflow (self, element):
        """ Given an element, find a graph model named like the element but with the appropriate suffix.
        Compile that model into a workflow. """

        elementName = element.getLabel ()
        compiler = self.createComponentCompiler (elementName, element.get (self.ATTR_VERSION))
        workflowName = self.formWorkflowName (element)
        modelName = self.formWorkflowSourceName (element)
        models = models = [ modelName ]

        ''' add context models '''
        for contextModel in self.contextModels:
            logger.debug ("ast:compile-workflow:add-context-model: %s", contextModel)
            models.append (contextModel)

        ''' load graphs '''
        compiler.parse (models)

        ''' If the element has a context element, perform substitutions. '''
        context = element.getContext ()
        if context:
            nodes = compiler.graph.getNodes ()
            for node in nodes:
                text = node.getType ()
                logger.debug ("ast:compile-wf:node: %s context: %s text: %s",
                              element.getLabel (),
                              context,
                              text)
                if text:
                    node.setType (self.replaceMapVariables (text, context))
                    logger.debug ("ast:compile-workflow:context:text: (%s)-> %s", node.getLabel (), node.getType ())
                literal = self.replaceMapVariables (node.getLabel (), context, recordMatches=node.getId (), workflowModel = compiler.workflowModel)
                node.setLabel (literal)

        ''' Compile and write output '''
        self.executeCompiler (compiler, elementName, workflowName)
        self.workflowCompiler [element.getId ()] = compiler

    def ast_compileSyntheticWorkflow (self, element, workflowName, graph, syntheticNode):
        """ Compile a synthetic workflow from a generated graph to an output file. """
        compiler = self.createComponentCompiler (workflowName, element.get (self.ATTR_VERSION))

        if len (graph.nodes) == 0:
            text = "each map operator"
            if element:
                text = "map operator: (%s)\n(%s)" % (element.getLabel (), element.getNode().getType ())
            if not self.isPackaging ():
                raise ValueError ("An empty synthetic graph was passed: Verify that map operators evaluate to non empty graphs in this environment for %s" % text)

        compiler.parse (self.contextModels, graph)
        compiler.compilerId = workflowName  #element.getLabel () #workflowName
        self.executeCompiler (compiler, element.getLabel (), workflowName)
        self.workflowCompiler [element.getId ()] = compiler
        self.workflowCompiler [syntheticNode.getId ()] = compiler

    #////////////////////////////////////////////////////////////
    #{ 5.0 Map Operator
    #////////////////////////////////////////////////////////////

    def replaceMapVariables (self, text, context, recordMatches = None, workflowModel = None):
        """ Replace map variables in the text of labels and properties of objects.

        This applies to sub-workflows or other object instances created by operators like map or aspect.
        """
        value = text

        variableMask = "${"
        mapVariableMask = "@{"
        
        mapExpressionPattern = re.compile ("@{(.*?)}", re.I|re.U)
        if not text:
            return
        
        for match in mapExpressionPattern.finditer (text):
            overall = match.group (0)
            expression = match.group (1)
            logger.debug ("ast:replace-map-vars:match: %s %s", overall, expression)
            isAnExpression = re.search ("[+\-\*\\/\%(\)\<\>\==]", expression)
            if isAnExpression:
                for key in context:
                    logger.debug ("ast:replace-map-vars:replace: %s %s in expr: %s", key, unicode (context[key]), expression)
                    expression = expression.replace (key, unicode (context[key]))
                text = text.replace (overall, unicode (eval (expression)))
            logger.debug ("ast:replace-map-vars:  outcome[%s]", text)

        if recordMatches and workflowModel and not value == text:
            workflowModel.addToVariableMap (value, text, recordMatches)

        value = text

        #if text and variableMask in text or mapVariableMask in text or '$' in text or '@' in text:
        if text and '$' in text or '@' in text:
            for contextKey in context:
                for pattern in [ "%s%s", "%s{%s}" ]:
                    orig_pattern = pattern % ("@", contextKey)
                    new_pattern = pattern % ("$", contextKey)
                    text = text.replace (orig_pattern, new_pattern)
            if text:
                template = Template (text)
                value = template.safe_substitute (context)
                logger.debug ("ast:replace-map-vars:  outcome[%s]", value)

        if recordMatches and workflowModel and not value == text:
            workflowModel.addToVariableMap (value, text, recordMatches)

        return value

    def getSyntheticId (self, baseId, prefix):
        """ Create a synthetic id given a base id and prefix """
        result = baseId
        id = -1
        if prefix in self.ctx().syntheticIds:
            self.ctx().syntheticIds[prefix] += 1
        else:
            self.ctx().syntheticIds[prefix] = 0
        id = self.ctx().syntheticIds[prefix]
        if id == -1:
            self.SYNTHETIC_ID += 1
            id = self.SYNTHETIC_ID
        result = "%s.%s" % (result, id)
        return result

    def nextLambdaId (self):
        value = self.LAMBDA_ID
        self.LAMBDA_ID = self.LAMBDA_ID + 1
        return value

    def ast_synthesizeInstance (self, graph, is_chained, last_instance, operator, operand, context, origins=[]):
        """ Execute map operator on an operand.
            i.   If operand is itself a map operator, execute the operand as a map operator
            ii.  If operand is a workflow, copy it
                    a. Registering a context object for later pattern replacement
                    b. Copying edges to and from copied object
                    c. Chaining between elements if chaining is on."""
        node = None
        type = operand.getType ()
        if type == self.MAP:
            ''' Recursively process a map operand which is itself a map operator '''
            targets = operand.getTargets (self.graph)
            for targetId in targets:
                target = self.getElement (targetId)
                if target:
                    node = self.ast_executeMapOperator (parent_graph  = graph,
                                                        operator      = operand,
                                                        element       = target,
                                                        input_context = context,
                                                        originEdges   = origins)
        else:
            ''' Create a new graph node replacing mapping parameters '''
            typeText = self.replaceMapVariables (operand.getNode().getType (), context)
            nodeId = self.getSyntheticId (operand.getId (), operand.getLabel ())
            nodeName = "%s.%s" % (operand.getLabel (), self.nextLambdaId ())
            node = graph.addNode (nodeId, nodeName, typeText)
            node.setContext (copy (context))

            ''' Map inputs to this synthetic instance copying input nodes to the synthetic graph. 
            origins = operator.getOrigins (self.graph)
            for sourceKey in origins:
                source = self.getElement (sourceKey)
                source = self.findOrCopy (source, graph)
                logger.debug ("add-edgex: %s %s", source.getLabel (), node.getLabel ())
                edgeId = "%s.%s" % (source.getId (), node.getId ())
                self.addEdge (graph, edgeId, source.getId (), node.getId ())
                '''

            ''' scox todo 
                '''
            for edge in origins:
                source = self.getElement (edge.getSource ())
                source = self.findOrCopy (source, graph)
                logger.debug ("newedge: %s %s", source.getLabel (), node.getLabel ())
                self.copyEdge (graph, edge, source, node)

            ''' if chaining is on, chain each instance to its predecessor node '''
            logger.debug ("is_chained (%s), last_instance(%s)", is_chained, last_instance)
            if is_chained and last_instance:
                parentId = last_instance.getId ()
                childId = node.getId ()
                graph.addEdge ("%s%s" % (parentId, childId), parentId, childId)
                logger.debug ("chained instance %s as parent of %s", parentId, childId)
        return node

    def ast_bindSyntheticNode (self, graph, operator, operand, nodeId, nodeLabel, nodeType, origins):
        """ Edit the graph to bind the synthetic node where the operand and operator were:
              i)   Create a new DAX node
              ii)  Point to it from the operators origin nodes
              iii) Point from it to the operands target nodes. """

        node = graph.addNode (nodeId, nodeLabel, nodeType)
        ''' scox todo
        for edge in origins:
            source = self.getElement (edge.getSource ())
            source = self.findOrCopy (source, graph)
            self.copyEdge (graph, edge, source, node)
            '''

        '''
        scox todo
            '''
        origins = operator.getOrigins (self.graph)
        for sourceKey in origins:
            source = self.getElement (sourceKey)
            if not source.getType () == self.MAP:
                source = self.findOrCopy (source, graph)
                logger.debug ("add-edgex: %s %s", source.getLabel (), node.getLabel ())
                edgeId = "%s.%s" % (source.getId (), node.getId ())
                self.addEdge (graph, edgeId, source.getId (), node.getId ())
                
        targets = operand.getTargetEdges (graph)
        for edge in targets:
            if not type(edge) == unicode: 
                target = self.getElement (edge.getTarget ())
                target = self.findOrCopy (target, graph)
                self.copyEdge (graph, edge, node, target)
        return node

    def ast_executeMapOperator (self, parent_graph, operator, element, input_context = {}, originEdges = []):
        """ Create a sub-graph to turn into a workflow
         Allow a sub-graph of only one node (a workflow or job)
         Only the operand the map operator points to will be duplicated.
         An operand which is itself an operator will be executed before emitting a sub-workflow. """
        FILE_PROTO = "file://"
        MAP_STYLE__CHAIN = "chain"
        MAP__STYLE = "style"
        MAP__VARIABLE = "variable"
        MAP__EACH = "each"
        MAP__START = "start"
        MAP__END = "end"

        MAP_STYLE__DYNAMIC = "dynamic"
        TAR_PROTO = "tar://"

        operator = self.ast_mapNode (operator.getNode ())
        variable = operator.get (MAP__VARIABLE)
        each = operator.get (MAP__EACH)
        is_chained = operator.get (MAP__STYLE) == MAP_STYLE__CHAIN
        is_dynamic = operator.get (MAP__STYLE) == MAP_STYLE__DYNAMIC

        logger.debug ("ast:map:each: %s type: %s variable: %s chained: %s",
                      each,
                      type (each),
                      variable,
                      is_chained)

        synthetic_graph = Graph ()
        last_instance = None
        context = {}

        for key in input_context:
            context [key] = input_context [key]

        inboundEdges = operator.getSourceEdges (self.graph)
        logger.debug ("ast:map:origin-edges")
        for edge in inboundEdges:
            edgeElement = self.getElement (edge.getId ())
            if edgeElement:
                source = self.getElement (edgeElement.getNode().getSource ())
                target = self.getElement (edgeElement.getNode().getTarget ())
                if edgeElement.getType () == self.INPUT:
                    logger.debug ("ast:map:origin-edge: inheriting edge (%s) from (%s, %s) to (%s, %s)",
                                   edgeElement.getId (),
                                   source.getId (),
                                   source.getLabel (),
                                   target.getId (),
                                   target.getLabel ())
                    originEdges.append (edge)

        if type(each) == dict:
            if MAP__START in each and MAP__END in each:
                start = int (each [MAP__START])
                end = int (each [MAP__END])
                for c in range (start, end):
                    logger.debug ("ast:map(%s)(loop)[start=%s,end=%s,cur=%s,element=%s]", self.compilerId, start, end, c, element.getLabel ())
                    context [variable] = c
                    last_instance = self.ast_synthesizeInstance (synthetic_graph,
                                                                 is_chained,
                                                                 last_instance,
                                                                 operator,
                                                                 element,
                                                                 context,
                                                                 originEdges)
        elif ( type(each) == str or type(each) == unicode):
            if string.find (each, FILE_PROTO) == 0:
                index = string.find (each, FILE_PROTO)
                expression = each [ index + len(FILE_PROTO): ]
                files = glob.glob (expression)
                files.sort ()
                for file in files:
                    logger.debug ("ast:map(%s)(glob)[item=%s,expression=%s,element=%s]", self.compilerId, file, expression, element.getLabel ())
                    file = file.replace (os.path.sep, "/")
                    context [variable] = file
                    basename = os.path.basename (file)
                    context ["%s_base" % variable] = basename
                    
                    #Publish each file via GridFTP from this host in the replica catalog. 
                    fileAbsolutePath = os.path.abspath (file)
                    fileURL = "gsiftp://%s/%s" % (socket.getfqdn (), fileAbsolutePath)
                    self.getReplicaCatalog().addEntry (basename, fileURL, self.ATTR_LOCAL)

                    # Register the file as a local file for later reference. 
                    self.compilerContext.localFileLocations [basename] = "file://%s" % fileAbsolutePath                
                    last_instance = self.ast_synthesizeInstance (synthetic_graph,
                                                                 is_chained,
                                                                 last_instance,
                                                                 operator,
                                                                 element,
                                                                 context,
                                                                 originEdges)
            elif is_dynamic:

                ''' Syntax: one input file. one target workflow. 

                Dynamic operators produce workflow components during the course of a workflow.
                This enables development of (corecursive) workflow algorighthms that respond to their own outpus.
                For an absurdly technical overview of corecursion: http://en.wikipedia.org/wiki/Corecursion
                '''

                ''' validate '''
                if not element.getType () == self.WORKFLOW:
                    raise SyntaxError ('Dynamic map operator [%s] points at element [%s] which is not a workflow. Dynamic map operators may only be applied to workflows' %
                                       (operator.getLabel (),
                                        element.getLabel () ) )
                if not "://" in each:
                    raise SyntaxError ('Invalid syntax for each=[%s] in dynamic map operator [%s]' % (each, operator.getLabel ()))

                mapType = 'tar' if each.startswith ('tar://') else None
                if not mapType:
                    raise SyntaxError ('Unrecognized input type [%s] derived from each=[%s] for dynamic map operator [%s]' % (mapType, each, operator.getLabel ()))


                inputFile = each.replace ('%s://' % mapType, '')
                index = operator.get ('index')

                keep = []
                for context in self.contextModels:
                    keep.append (os.path.basename (context))

                contextModels = os.pathsep.join (keep)
                instanceArgs = element.get ('instanceArgs')
                logger.debug ("instanceargs: %s %s %s", instanceArgs, element, element.getId ())

                configuration = {
                    'outputName'    : element.getLabel (),
                    'modelPath'     : os.pathsep.join (self.getModelPath ()),
                    'outputDir'     : self.getOutputDir (),
                    'contextModels' : contextModels,
                    'sites'         : self.getSites () ,
                    'graysonHome'   : self.getProperty (self.MAP)[self.GRAYSON_HOME],
                    'appHome'       : self.getProperty (self.MAP)[self.APP_HOME],
                    'operator'      : {
                        "type"      : 'dynamicMap',
                        'method'    : 'tar',
                        'input'     : inputFile,
                        'variable'  : variable,
                        'index'     : index,
                        'namespace' : element.getLabel (),
                        'instanceArgs' : instanceArgs if instanceArgs else "",
                        'version'   : '1.0',
                        'flow'      : '%s.%s' % (element.getLabel (), self.MODEL_SUFFIX)
                        }
                    }
                config = os.path.join (self.getOutputDir (), "%s.grayconf" % operator.getLabel ())
                GraysonUtil.writeFile (config, json.dumps (configuration, indent=4, sort_keys=True))

                ld_library_path = os.environ ["LD_LIBRARY_PATH"] if "LD_LIBRARY_PATH" in os.environ else ""

                jobType = {
                    "type"     : "job",
                    "args"     : "--configuration=%s " % config,
                    "profiles" : {
                        "env"  : {
                            "PYTHONPATH"      : os.environ ['PYTHONPATH'],
                            "GRAYSON_HOME"    : os.environ ['GRAYSON_HOME'],
                            "PATH"            : os.environ ['PATH'],
                            "LD_LIBRARY_PATH" : ld_library_path,
                            "GLOBUS_LOCATION" : os.environ ['GLOBUS_LOCATION'],
                            "CONDOR_HOME"     : os.environ ['CONDOR_HOME']
                            }
                        }
                    }

                if 'profiles' in operator.getProperties ():
                    jobType ['profiles'] = operator ['profiles']
                    
                origins = operator.getSourceEdges (self.graph)

                outputPatterns = [
                    os.path.join (self.getOutputDir (), "%s*.dax" % element.getLabel ()),
                    os.path.join (self.getOutputDir (), "%s.grayconf" % element.getLabel ())
                    ]
                for pattern in outputPatterns:
                    oldOutputs = glob.glob (pattern)
                    logging.debug (" old output scan for: %s \n   %s", pattern, oldOutputs)
                    for output in oldOutputs:
                        logging.debug ("removing old output: %s", output)
                        os.remove (output)

                job = self.graft (old = operator,
                                  new = self.ast_addNode (id      = operator.getId (),
                                                          label   = operator.getLabel (),
                                                          typeObj = jobType))
                for edge in origins:
                    source = self.getElement (edge.getSource ())

                    output = self.ast_addNode (id      = "%s_synth" % source.getId (),
                                               label   = source.getLabel (),
                                               typeObj = { 'type' : 'reference' });
                    job.getContext ()['allowCycle'] = True

                    self.copyEdge (self.graph, edge, job.getNode (), output)
                    self.copyEdge (self.graph, edge, output.getNode (), element)

                    
                '''
                Make a reference from the graysonc compiler to the new job.
                Create the concrete executable reference to the compiler if it has not been created yet. '''
                exe = self.synthesizeExecutable (targetJob = job,
                                                 label     = "graysonc",
                                                 path      = self.getProperty (self.MAP)['graysonHome'])
                
                ''' Make inheritance work for dynamically added objects '''
                operatorReferences = self.getReferenceByLabel (operator.getLabel ())
                if operatorReferences:
                    logger.debug ("--(map): found existing %s reference.", operator.getLabel ())
                    origins = operatorReferences.getOrigins (self.graph)                    
                    for originId in origins:
                        origin = self.getElement (originId)
                        logger.debug ("--(map): adding origin %s of %s executable.", origin.getLabel (), operator.getLabel ())
                        exe.addAncestor (origin)

                ''' Ensure we dont plan this job to some other site - its installed here. '''
                exeProps = exe.getProperties () 
                exeProps ['installed'] = 'true'

                ''' Re-cast the operand workflow as a dax. Add the --basename argument needed for dynamic invocation. '''
                args = element.get (self.ATTR_ARGS)
                originalArgs = ' '.join (args) if isinstance (args, list) else args if args else ''
                logger.debug ("mapped dax %s original args: %s", element.getLabel (), originalArgs)
                typeObj = {
                    "type" : "dax",
                    "args" : ''.join ([
                            "%s --basename %s" % (originalArgs, element.getLabel ()),
                            "   --sites %s" % self.getSites ()
                            ])
                    }
                dax = self.graft (old = element,
                                  new = self.ast_addNode (id      = element.getId (),
                                                          label   = element.getLabel (),
                                                          typeObj = typeObj))
                logger.debug ("removed %s and grafted new: %s", element.getLabel (), dax.getProperties ())
                
                if self.isPackaging ():
                    ''' get this file recorded as a referenced model. '''
                    self.ast_compileWorkflow (element)

        '''
        The map operators operand has been mapped to concrete instances
           (a) Generated synthetic instances are in synthetic_graph.
           (b) The synthetic_graph is about to be emitted as an executable workflow
           (c) Edit parent_graph to bind the synthetic node where the operator/operand were
         '''
        syntheticNode = None
        if not is_dynamic:
            syntheticId = self.getSyntheticId (operator.getId (), operator.getLabel ())
            number = syntheticId.split(".")[1]
            syntheticLabel = "%s.%s" % (operator.getLabel (), number)

            logger.debug ("yeah todo --- %s ", syntheticLabel)

            syntheticType = '{ "type" : "dax" }'
            syntheticNode = self.ast_bindSyntheticNode (parent_graph,
                                                        operator,
                                                        element,
                                                        syntheticId,
                                                        syntheticLabel,
                                                        syntheticType,
                                                        originEdges)

            logger.debug ("add-synth-node: (%s) added to synthgraph of operator (%s)", syntheticNode.getLabel (), operator.getLabel ())
            workflowName = "%s.%s" % (syntheticNode.getLabel (), self.DAX)
            workflowName = self.replaceMapVariables (workflowName, input_context)

            self.ast_compileSyntheticWorkflow (operator, workflowName, synthetic_graph, syntheticNode)

        return syntheticNode

    def copyEdge (self, graph, edge, source, target, edgeType=None):
        """ Copy the edge into the specified graph. """
        edgeId = "%s.%s" % (edge.getId (), target.getId ())
        if not edgeType:
            edgeType = edge.getType ()
        edgeCopy = self.addEdge (graph, edgeId, source.getId (), target.getId (), edgeType)
        logger.debug ("qqq ast:copy-edge: from (%s(%s)->%s(%s))type(%s)",
                       source.getLabel (),
                       source.getId (),
                       target.getLabel (),
                       target.getId (),
                       edgeType)
        return edgeCopy
    
    def addEdge (self, graph, edgeId, sourceId, targetId, type=''):
        """ Add the specified edge to the graph. """
        edge = graph.addEdge (edgeId, sourceId, targetId, type)
        self.ast_mapEdge (edge)
        logger.debug ("ast:add-edge: id(%s) srcid(%s) targid(%s) type(%s)",
                      edgeId, sourceId, targetId, type)
        return edge
    
    def findOrCopy (self, element, graph):
        """ Copy the element into the graph if it isnt already there. """
        end_element = graph.getNodeByLabel (element.getLabel ())
        if not end_element:
            end_element = graph.addNode ("%s_synth" % element.getId (),
                                         element.getLabel (),
                                         element.getNode().getType ())
        return end_element

    def ast_finalizeMapOperator (self, operator, element=None):
        """ Remove the map operator element once it has been executed. """
        logger.debug ("ast:map:finalize %s", element)
        self.removeElement (operator.getId ())
        if element:
            if element.getType () == self.MAP:
                targets = element.getTargets (self.graph)
                for targetId in targets:
                    target = self.getElement (targetId)
                    if target:
                        self.ast_finalizeMapOperator (element, target)
            else:
                logger.debug ("ast:map:finalize operand: %s", element.getLabel ())
                self.removeElement (element.getId ())

    def ast_getMapTargets (self, operator):
        """ Get operands of the map operator. """
        targetEdges = []
        edges = operator.getTargetEdges (self.graph)
        for edge in edges:
            target = self.getElement (edge.getTarget ())
            if target.getType () == self.MAP:
                operandTargets = self.ast_getMapTargets (target)
                for item in operandTargets:
                    targetEdges.append (item)
            else:
                edges = target.getTargetEdges (self.graph)
                for e in edges:
                    targetEdges.append (e)
        return targetEdges

    def ast_processMapOperators (self):
        """ Execute map operators. 
        Look for roots - map operators which are not operands of other map operators.
        Execute recursively from the roots."""
        operators = self.getElementsByType (self.MAP)
        if operators:
            for operator in operators:
                logger.debug ("map:operator:execute %s", operator.getLabel ())
                sources = operator.getOrigins (self.graph)
                isRoot = True
                for sourceId in sources:
                    source = self.getElement (sourceId)
                    if not source:
                        logger.debug ("map:operator: couldn't find %s" % sourceId)
                    elif source.getType () == self.MAP:
                        isRoot = False
                        break
                if isRoot:
                    ''' execute the operator for each mapped object '''
                    logger.debug ("map:operator:collect: targets: %s", operator.getLabel ())
                    targets = operator.getTargets (self.graph)

                    # TODO: single constant. 
                    MAP__STYLE = "style"
                    MAP_STYLE__DYNAMIC = "dynamic"
                    is_dynamic = operator.get (MAP__STYLE) == MAP_STYLE__DYNAMIC

                    for targetId in targets:
                        target = self.getElement (targetId)
                        if target:
                            logger.debug ("map:operator:executing: for target: %s", target.getLabel ())
                            targetEdges = []
                            node = self.ast_executeMapOperator (parent_graph=self.graph,
                                                                operator=operator,
                                                                element=target,
                                                                input_context={},
                                                                originEdges=[])
                            if not is_dynamic:
                                ''' add the results of the map operator execution into the graph '''
                                self.graph.addExistingNode (node)
                                self.ast_mapNode (node)

                                targetEdges = self.ast_getMapTargets (operator)
                                for edge in targetEdges:
                                    if not type(edge) == unicode and not type(edge) == str:
                                        target = self.getElement (edge.getTarget ())
                                        self.copyEdge (self.graph, edge, node, target)
                                logger.debug ("map:operator: added synthetic dax node: %s (%s)",
                                              node.getLabel (),
                                              node.getType ())
                    if is_dynamic:
                        self.ast_finalizeMapOperator (operator)
                    else:
                        for targetId in targets:
                            target = self.getElement (targetId)
                            if (target):
                                self.ast_finalizeMapOperator (operator, target)

    #////////////////////////////////////////////////////////////
    #{ 6.0 Aspects
    #////////////////////////////////////////////////////////////

    def ast_weaveJobAdvice (self):
        jobs = self.getElementsByType ( [ self.JOB, self.WORKFLOW, self.DAX ] )
        seen = []
        for job in jobs:            
            if job.getId () in seen:
                continue

            logger.debug ("ast:weaveJobAdvice: job(%s)", job.getLabel ())
            for pointcut in self.compilerContext.aspects:

                logger.debug ("ast:job-advice:pointcut: (%s)", pointcut.getLabel ())
                if not pointcut.getType () == self.ASPECT_POINTCUT:
                    continue

                afterPattern  = pointcut.get (self.ASPECT_AFTER)
                beforePattern = pointcut.get (self.ASPECT_BEFORE)
                aspectName    = pointcut.get (self.ASPECT)

                targetLabel   = job.getLabel ()
                matchesBefore = re.search (beforePattern, targetLabel) if beforePattern else None
                matchesAfter  = re.search (afterPattern, targetLabel) if afterPattern else None

                if matchesBefore:
                    logger.debug ("weave-job-advice(before): job=%s id=%s type=%s pointcut=%s", job.getLabel (), job.getId (), job.getType (), pointcut.getLabel ())
                    aspectInstance = self.ast_weaveAspectCompileAspect (pointcut, aspectName, job)
                    edge = self.addEdge (graph    = self.graph,
                                         edgeId   = "%s_asp_%s" % (aspectInstance.getId (), job.getId ()),
                                         sourceId = aspectInstance.getId (),
                                         targetId = job.getId ())
                if matchesAfter:
                    logger.debug ("weave-job-advice(before): job=%s id=%s type=%s pointcut=%s", job.getLabel (), job.getId (), job.getType (), pointcut.getLabel ())
                    aspectInstance = self.ast_weaveAspectCompileAspect (pointcut, aspectName, job)
                    edge = self.addEdge (graph    = self.graph,
                                         edgeId   = "%s_asp_%s" % (aspectInstance.getId (), job.getId ()),
                                         sourceId = job.getId (),
                                         targetId = aspectInstance.getId ())

                seen.append (job.getId ())

    def ast_weaveAspects (self):
        """
        An aspect is a workflow woven into another workflow by the compiler.
        
        Pointcuts are specifications that map an aspect onto edges in a graph.
        
        After mapNodes and mapEdges
        For each edge 
          Read the aspect pointcut instructions
          For each matching node in the graph:
             Create a component workflow representing the aspect graph (i.e. traditional subworkflow)
             Insert the node at the right position in the graph
             """

        ''' weave advice for job advice (before and after pointcuts for  jobs). '''
        self.ast_weaveJobAdvice ()


        aspectActivations = {}
        logger.debug ("ast:aspect:weave")

        edges = self.graph.getEdges ()
        for edge in edges:
            source = self.getElement (edge.getSource ())
            target = self.getElement (edge.getTarget ())
            if not source:
                continue
            if not target:
                continue
            logger.debug ("ast:aspect:weave:got: (source=%s) (target=%s)", source.getLabel (), target.getLabel ())
            ''' get pointcuts '''
            for pointcut in self.compilerContext.aspects:
                if not pointcut.getType () == self.ASPECT_POINTCUT:
                    continue

                fromElement = pointcut.get (self.ASPECT_FROM)
                toElement = pointcut.get (self.ASPECT_TO)
                variable = pointcut.get (self.VARIABLE)
                pattern = pointcut.get (self.PATTERN)
                aspectName = pointcut.get (self.ASPECT)

                afterPattern  = pointcut.get (self.ASPECT_AFTER)
                beforePattern = pointcut.get (self.ASPECT_BEFORE)
                
                if beforePattern or afterPattern:
                    continue

                if not toElement and not fromElement:
                    raise ValueError ("an aspect must have either 'to' or 'from' node specified")
                if not pattern:
                    raise ValueError ("an aspect must specify a file pattern")
                if not aspectName:
                    raise ValueError ("unable to determine aspect name for pointcut %s " % pointcut.getProperties ())

                jobNode     = source
                fileElement = target
                jobPattern  = fromElement
                if toElement:
                    fileElement = source
                    jobNode     = target
                    jobPattern  = toElement

                targetLabel = jobNode.getLabel ()
                matchesJob = re.search (jobPattern, targetLabel)
                matchesFile = re.search (pattern, fileElement.getLabel ())

                logger.debug ("weave:egg:match---- pat:%s file:%s jobpat:%s job:%s %s",
                              pattern,
                              fileElement.getLabel (),
                              jobPattern, jobNode.getLabel (),
                              pointcut.getId ())

                activationKey = "edge(%s)-point(%s)-job(%s)-file(%s)-cid(%s)" % (edge.getId (),
                                                                                 pointcut.getId (),
                                                                                 jobNode.getId (),
                                                                                 fileElement.getId (),
                                                                                 self.compilerId)

                if matchesJob and matchesFile:

                    logger.debug ("[aspect-apply]: %s job:%s file:%s from: %s, patt: %s",
                                  activationKey,
                                  jobNode.getLabel (),
                                  fileElement.getLabel (),
                                  fromElement,
                                  pattern)
                    aspectActivations [activationKey] = pointcut

                    if toElement:
                        self.ast_weaveAspectFromFileToJob (pointcut    = pointcut,
                                                           edge        = edge,
                                                           aspectName  = aspectName,
                                                           jobNode     = jobNode,
                                                           fileElement = fileElement,
                                                           variable    = variable)
                    elif fromElement:
                        self.ast_weaveAspectFromJobToFile (pointcut    = pointcut,
                                                           edge        = edge,
                                                           aspectName  = aspectName,
                                                           jobNode     = jobNode,
                                                           fileElement = fileElement,
                                                           variable    = variable)

    def ast_weaveAspectCompileAspect (self, pointcut, aspectName, jobNode, variableValue=None, variable=None):
        logger.debug ("--weaving: compile aspect workflow")
        synthId = self.getSyntheticId (jobNode.getId (), aspectName)

        ''' Use the dynamic index if one is provided '''
        dynamicIndex = Operator.getDynamicIndex (self.getInputModelProperties ())
        if dynamicIndex:
            number = dynamicIndex
        else:
            number = synthId.split(".")[1]

        typeObj = pointcut.get ("instanceType")
        if not typeObj:
            typeObj = { 'type' : 'workflow' }

        if not variable:
            variable = ""
            variableValue = ""

        aspectElement = self.ast_addNode (id      = "%s.%s" % (aspectName, synthId),
                                          label   = "%s.%s" % (aspectName, number),
                                          typeObj = typeObj,
                                          context = { variable : variableValue })
        aspectElement.getContext ()['allowCycle'] = True

        self.ast_compileWorkflow (aspectElement);
        
        logger.debug ("--weaving: generated synthetic aspect node name=(%s) id=(%s) from=(%s) cid=(%s)",
                      aspectElement.getLabel (),
                      aspectElement.getId (),
                      variableValue,
                      self.compilerId)
        return aspectElement 

    def ast_weaveAspectCreateSynthFile (self, fileElement):
        logger.debug ("--weaving: generating synthetic file node type(%s)", fileElement.getNode().getType ())
        synthFileId = "%s.%s" % (fileElement.getId (), self.getSyntheticId (fileElement.getId (), fileElement.getLabel ()))
        return self.ast_addNode (id      = synthFileId,
                                 label   = fileElement.getLabel (),
                                 typeObj = { "type" : "reference" })

    def ast_weaveAspectCreateChain (self, edge, first, second, third):
        logger.debug ("--weaving: generating synthetic edge")
        if first:
            edgeOne = self.copyEdge (self.graph, edge, second, first)
        edgeTwo = self.copyEdge (self.graph, edge, third, second)

    def ast_weaveAspectRepointTargets (self, fileElement, synthFileElement, aspectElement):
        logger.debug ("--weaving: remapping old file targets to use synth file as target")
        targetEdges = fileElement.getTargetEdges (self.graph)
        for targetEdge in targetEdges:
            fileTarget = targetEdge.getTarget ()
            ''' never target the synthetic file at the aspect which is now a target of the original file. '''
            if not fileTarget == aspectElement.getId ():
                target = self.getElement (targetEdge.getTarget ())
                logger.debug ("   synth file element now points to %s ", target.getLabel ())
                targetEdge.setSource (synthFileElement.getId ())

    def ast_weaveAspectRepointSources (self, fileElement, synthFileElement, aspectElement):
        logger.debug ("--weaving: remapping old file sources to use synth file as source")
        edges = self.graph.getEdges ()
        for edge in edges:
            if edge.getSource () == fileElement.getId ():
                targetId = edge.getTarget ()
                if not targetId == aspectElement.getId ():
                    edge.setSource (synthFileElement.getId ())

    def ast_weaveAspectFromFileToJob (self, pointcut, edge, aspectName, jobNode, fileElement, variable):
        aspectElement    = self.ast_weaveAspectCompileAspect (pointcut, aspectName, jobNode, fileElement.getLabel (), variable)
        synthFileElement = self.ast_weaveAspectCreateSynthFile (fileElement)
        self.ast_weaveAspectCreateChain (edge, fileElement, aspectElement, synthFileElement)
        self.ast_weaveAspectRepointSources (fileElement, synthFileElement, aspectElement)

    def ast_weaveAspectFromJobToFile (self, pointcut, edge, aspectName, jobNode, fileElement, variable):
        aspectElement    = self.ast_weaveAspectCompileAspect (pointcut, aspectName, jobNode, fileElement.getLabel (), variable)
        synthFileElement = self.ast_weaveAspectCreateSynthFile (fileElement)
        self.ast_weaveAspectCreateChain (edge, synthFileElement, aspectElement, fileElement)
        self.ast_weaveAspectRepointTargets (fileElement, synthFileElement, aspectElement)

    def setInboundEdgesTarget (self, old, new, skip=[]):
        """Make all edges formerly pointing to old point to new. Skip any ids in the skip list."""
        edges = old.getTargetEdges (self.graph)
        logger.debug ("   ast:target-edges: %s", edges)
        for edge in edges:
            logger.debug ("     ast:source=%s target=%s", edge.getSource(), edge.getTarget ())
            source = self.getElement (edge.getSource ())
            targetId = edge.getTarget ()
            target = self.getElement (targetId)
            if target and source and not targetId in skip:
                logger.debug ("   ast:re-target: (%s/%s) -> %s", source.getLabel (), new.getLabel (), target.getLabel ())
                edge.setSource (new.getId ())
                
    def setOutboundEdgesSource (self, old, new, skip=[]):
        """Make all edges originating at old now originate at new. Skip any ids in the skip list."""
        edges = old.getSourceEdges (self.graph)
        logger.debug ("   ast:source-edges: %s", edges)
        for edge in edges:
            sourceId = edge.getSource ()
            source = self.getElement (sourceId)
            target = self.getElement (edge.getTarget ())
            if not sourceId in skip and target and not target.getId () == new.getId ():
                logger.debug ("   ast:re-source: %s -> (%s/%s)", source.getLabel (), target.getLabel (), new.getLabel ())
                edge.setTarget (new.getId ())

    def graft (self, old, new):
        """ Make edges that used to point to old point to new.
        Make edges that used to start at old start at new.
        Remove the old element.
        Add the new element.
        """
        oldAsSourceEdges = old.getTargetEdges (self.graph)
        for edge in oldAsSourceEdges:
            edge.setSource (new.getId ())
        oldAsTargetEdges = old.getSourceEdges (self.graph)
        for edge in oldAsTargetEdges:
            edge.setTarget (new.getId ())

        #self.setInboundEdgesTarget (old, new)
        #self.setOutboundEdgesSource (old, new)
        logger.debug ("graft: removing original node: %s", old.getLabel ())
        self.removeElement (old.getId (), removeEdges=False)
        self.addElement (new.getId (), new)
        return new

    #////////////////////////////////////////////////////////////
    #{ 7.0 AST Steps
    #////////////////////////////////////////////////////////////

    def ast_createDependencies (self, daxContext):
        """ Determine job precedence and record these. Also recognize root jobs. """
        logger.debug ("ast:dependencies:")
        self.roots = []
        wmsjobs = daxContext.getWmsJobs ()
        for jobId in wmsjobs:
            job = daxContext.getWmsJob (jobId)
            logger.debug ("ast:dependency:job-id: %s" % jobId)
            dependencySet = daxContext.getDependencies (jobId)
            if dependencySet:
                for key in dependencySet:
                    dependency = None
                    logger.debug ("ast:dependency:key: (%s)" % key)
                    dependency = daxContext.getWmsJob (key)
                    if dependency:
                        logger.debug ("ast:dependency:add: (%s)=>(%s)" % (jobId, key))
                        self.workflowModel.addDependency (parent=dependency, child=job)
            else:
                logger.debug ("ast:dependency: add root job (%s)", jobId)
                self.roots.append (jobId)

    def ast_properties (self):        
        """ Build aggregate properties based on property nodes in all read graphs """
        logger.debug ("ast:prop:init")
        properties = self.compilerContext.properties.getProperties ()
        if not self.MAP in properties:
            properties [self.MAP] = {}
        properties [self.MAP][self.GRAYSON_HOME] = os.environ ["GRAYSON_HOME"]
        graysonHome = path = self.getProperty (self.MAP)[self.GRAYSON_HOME]
        for path in [ os.path.join (graysonHome, 'var'), os.path.join (graysonHome, '..', 'var') ]:
            if os.path.isdir (path):
                properties [self.MAP][self.GRAYSON_VAR] = path
        properties [self.MAP][self.APP_HOME] = self.appHome.replace ("\\", "/")
        properties [self.MAP][self.OUTPUT_DIR] = self.getOutputDir ()
        properties [self.MAP][self.FQDN] = socket.getfqdn ()

        ''' Aggregate each properties object encountered by the parser. '''
        propertyNodes = self.graph.getPropertyList ()
        for propertyNode in propertyNodes:
            element = ASTElement (propertyNode)
            self.compilerContext.properties.mergePropertiesFrom (element)
            logger.debug ("ast:prop:update: %s", self.compilerContext.properties.getProperties ())

        ''' If command line properties were given, override using those. '''
        basics = properties [self.MAP]
        for key in self.getInputModelProperties ():
            value = self.getInputModelProperties() [key]

            logger.debug ("ast:prop:adding model property %s = %s", key, value)
            if value:
                valueTemplate = Template (value)
                value = valueTemplate.safe_substitute (basics)

            properties [self.MAP][key] = value

        ''' If execution mode is shell, configure the workflow management system appropriately '''
        if self.EXECUTION_MODE in basics and basics[self.EXECUTION_MODE] == self.EXECUTION_MODE__SHELL:
            logger.debug ("setting shell execution mode for workflow: %s", self.compilerId)
            self.getWorkflowManagementSystem().enableShellExecution ()

        if self.DATA_CONFIGURATION in basics:
            dataConfiguration = basics [self.DATA_CONFIGURATION]
            logger.debug ("setting data configuration: %s", dataConfiguration)
            self.getWorkflowManagementSystem().setDataConfiguration (dataConfiguration)
            
        self.compilerContext.isDynamicOperator = Operator.DYNAMIC_INDEX in self.getInputModelProperties ()
        logger.debug ("isdynamicoperator: setprop: %s", self.compilerContext.isDynamicOperator)
        logger.debug ("isdynamicoperator: props: %s", self.getInputModelProperties ())

        logger.debug (properties)

    def ast_replaceProperties (self, text):
        """
        Replace properties in a string using the compiler property context.
        """
        context = self.getProperty ("map")
        if not context:
            context = {}
        if text and "$" in text:
            logger.debug ("ast:replaceprop: txt:%s \n map:%s",
                          text.replace ("\n", " "),
                          json.dumps (context).replace ("\n", " "))
            template = Template (text)
            text = template.safe_substitute (context)
        return text

    def ast_mapNode (self, node):
        """
        Given a graph node, create an abstract syntax element.
        Replace any properties referenced in the nodes attributes.
        Read the nodes attributes and make those properties of the new AST element.
        """
        node.setLabel (self.ast_replaceProperties (node.getLabel ()))
        text = node.getType ()
        if text and '$' in text:
            try:
                node.setType (self.ast_replaceProperties (node.getType ()))
                logger.debug ("ast:map-node:settype: (%s)" % text)
            except TypeError as e:
                logger.error ("context: %s\ntype: %s", context, text)
            except KeyError as e:
                self.addError ("property %s is not defined for element: %s" % (sys.exc_value, node.getLabel ()))
                traceback.print_exc (e)
                raise e
        element = ASTElement (node)
        logger.debug ("ast:map-node:add-element: label=(%s) type=(%s)", element.getLabel (), node.getType ())
        self.addElement (node.getId (), element)
        return element

    def ast_mapStaticNode (self, node):
        """ Load any nodes without variables as AST elements."""
        element = None
        jsonText = node.getType ()
        if jsonText and not "$" in jsonText:
            node.setType (jsonText)
            element = ASTElement (node)
            logger.debug ("ast:map-static:mapping[%s]: %s %s %s)", self.compilerId, node.getId(), node.getLabel (), node.getType ())
            self.addElement (node.getId (), element)
        return element

    def ast_synthesizeExecutables (self):
        executableElement = None
        """ For each job in the graph, check if it has an associated executable.
        If not, synthesize executables where needed by creating an object based on the name of the job. """
        elements = self.getElementsByType (self.JOB)
        for element in elements:
            logger.debug ("ast:synthesize-executable: job(%s)", element.getLabel ())
            origins = element.getSourceEdges (self.graph)
            missingExecutable = True
            for originId in origins:
                origin = self.getElement (originId)
                if origin and origin.getType () == self.EXECUTABLE:
                    missingExecutable = False
                    break
            if missingExecutable:
                self.synthesizeExecutable (targetJob = element)
        return executableElement

    def synthesizeExecutable (self, targetJob, label=None, path=None):
        executableElement = None
        """ Create an executable based on the name of a target job."""
        executableRef = self.ast_addNode (id       = '%s_exe_ref' % targetJob.getId (),
                                          label    = '%s.sh'  % targetJob.getLabel (),
                                          typeObj  = '{ "type" : "reference" }' )
        edge = self.addEdge (graph    = self.graph,
                             edgeId   = '%s_exe_edge' % targetJob.getId (),
                             sourceId = executableRef.getId (),
                             targetId = targetJob.getId ())
        logger.debug ("ast:synthesize-reference-to-executable: id(%s) label(%s) type(%s)",
                      executableRef.getId (), 
                      executableRef.getLabel (), 
                      executableRef.getType ())

        concrete = self.getElementByLabel ("%s.sh" % targetJob.getLabel ())
        if not concrete:
            #appHome = None
            if not path:
                #appHome = self.getProperty (self.MAP)[self.APP_HOME]
                path = self.getProperty (self.MAP)[self.APP_HOME]
            if not label:
                label = targetJob.getLabel ()

            testPath = "%s/bin/%s.sh" % (path, label)
            if os.path.exists (testPath):
                path = testPath
            else:
                testPath = "%s/bin/%s" % (path, label)                
                if os.path.exists (testPath):
                    path = testPath
                else:
                    logger.warning ("unable to determine path for executable. last tried: %s", testPath)

            executableType = {
                "type" : "executable",
                "path" : path #"%s/bin/%s.sh" % (path, label)
                #"installed" : "true" #(required for shell mode)
                }
            executableElement = self.ast_addNode (id       = '%s_exe' % targetJob.getId (),
                                                  label    = '%s.sh'  % targetJob.getLabel (),
                                                  typeObj  = json.dumps (executableType))
            logger.debug ("ast:synthesize-executable: id(%s) label(%s) type(%s)",
                          executableElement.getId (), 
                          executableElement.getLabel (), 
                          executableElement.getType ())
        return executableElement
        
    def ast_addNode (self, id, label, typeObj, context=None):
        """ Add a node ot the model. """
        if isinstance (typeObj, dict):
            typeObj = json.dumps (typeObj)
        node = self.graph.addNode ("%s_synth" % id, label, typeObj)
        if (context):
            node.setContext (context)
        return self.ast_mapNode (node)
    
    def ast_mapNodes (self):
        """ Map nodes (and property resolution).
        1. Map static nodes.
        2. Load imported context models.
        3. For the top context model, build subworkflows.
        4. For others
          5. Resolve object properties
          6.  Configure execution sites
          7. Map nodes in the graph as AST elements
          8. Execute map operators 
          9. Synthesize tacit executables
          10. Detect and register aspect pointcuts
          11. Weave aspects
          12. Register jobs and daxes
          13. Generate sub-workflows
        """
        jobs = []
        logger.debug ("ast:map-nodes: (cid=%s)", self.compilerId)

        ''' read existing nodes and map them '''
        nodes = self.graph.getNodes ()
        for node in nodes:
            self.ast_mapStaticNode (node)
        
        ''' load context models '''
        logger.debug ("is-top-model: %s", self.isTopModel ())
        if self.isTopModel ():
            contextModelElements = self.getElementsByType (self.CONTEXT_MODEL)
            contextModelFiles = []
            for contextModel in contextModelElements:
                fileName = "%s%s" % (contextModel.getLabel (), self.CONTEXT_MODEL_TAG)
                if not fileName in self.getTopModel ():
                    contextModelFiles.append (fileName)
            if len(contextModelFiles) > 0:
                compilerId = self.compilerId
                self.parse (contextModelFiles, self.graph)
                self.compilerId = compilerId

        if self.isContextModel ():
            if self.isTopModel () and not Operator.isDynamicOperator (self):
                self.ast_buildSubWorkflows (jobs)
        else:
            ''' resolve properties '''
            self.ast_properties ()

            ''' recognize configured sites '''
            self.configureSites ()

            ''' map nodes in the graph '''
            nodes = self.graph.getNodes ()
            for node in nodes:
                self.ast_mapNode (node)

            ''' expand map operators '''
            self.ast_processMapOperators ()
            edgeElements = self.ast_mapEdges ()

            ''' assume executable references based on job names for jobs with no exes '''
            self.ast_synthesizeExecutables ()

            ''' register aspects '''
            aspectElements = self.getElementsByType (self.ASPECT)
            for aspect in aspectElements:

                ''' Aspects linked to workflow via pointcut edges. probably get rid of this approach in favor of the later syntax. '''
                pointcuts = aspect.getTargetEdges (self.graph)
                for pointcut in pointcuts:
                    aspectTarget = pointcut.getTarget ()
                    aspect = self.getElement (pointcut.getSource ())
                    pointcutElement = self.getElement (pointcut.getId ())
                    pointcutElement.set (self.ASPECT, aspect.getLabel ())
                    self.ast_addPointcut (pointcutElement)

                ''' Embedded pointcuts - all information is in the object itself. '''
                pointcuts = aspect.get ("pointcuts")
                if pointcuts:
                    for key in pointcuts:
                        pointcut = pointcuts [key]

                        pointcutElement = self.ast_addNode (id      = "%s.%s" % (aspect.getId (), key),
                                                            label   = key,
                                                            typeObj = pointcut)
                        pointcutElement.set (self.ASPECT, aspect.getLabel ())
                        pointcutElement.set (self.ATTR_TYPE, self.ASPECT_POINTCUT)
                        self.ast_addPointcut (pointcutElement)

            ''' weave aspects '''
            self.ast_weaveAspects ()
            
            ''' register jobs and daxes '''
            seenJobs = [] # todo: understand why there are duplicates in the first place 
            for elementType in [ self.JOB, self.DAX ]:
                elements = self.getElementsByType (elementType)
                for element in elements:
                    logger.debug ("ast:map-nodes: candidate job: %s", element.getLabel ())
                    if not element.getLabel () in seenJobs:
                        seenJobs.append (element.getLabel ())
                        logger.debug ("ast:map-nodes: register job: %s", element.getLabel ())
                        jobs.append (element)

            if not Operator.isDynamicOperator (self):
                self.ast_buildSubWorkflows (jobs)
        return jobs

    def ast_addPointcut (self, pointcutElement):
        logger.debug ("ast:register-aspect: (%s) %s", pointcutElement.getLabel (), pointcutElement.getType ())
        
        # tragic really. todo: fix root cause of dups. 
        pointcutKey = "from(%s)-to(%s)-patt(%s)-before(%s)-after(%s)" % (pointcutElement.get (self.ASPECT_FROM),
                                                                         pointcutElement.get (self.ASPECT_TO),
                                                                         pointcutElement.get (self.PATTERN),
                                                                         pointcutElement.get (self.ASPECT_BEFORE),
                                                                         pointcutElement.get (self.ASPECT_AFTER))
        if not pointcutKey in self.compilerContext.seenPointcuts:
            self.compilerContext.seenPointcuts [pointcutKey] = pointcutElement.getId ()
            self.compilerContext.aspects.append (pointcutElement)                

    def ast_buildSubWorkflows (self, jobs):
        """ Build Sub Workflows: Compile each sub-workflow object. """

        ''' build sub workflows '''
        elements = self.getElementsByType (self.WORKFLOW)
        for element in elements:
            if not element.getLabel () in self.compilerContext.processedWorkflows:
                logger.debug ("ast:map-nodes: register workflow: %s %s", element.getLabel (), self.compilerId)
                self.compilerContext.processedWorkflows.append (element.getLabel ())
                if not element.get ("compile") == "no":
                    jobs.append (element)
                    args = element.get (self.ATTR_ARGS)
                    if not args:
                        args = self.getExecuteArguments ()
                        logger.debug ("ast:map-nodes: set workflow args %s: %s", element.getLabel (), args)
                        element.set (self.ATTR_ARGS, args)
                        self.ast_compileWorkflow (element)
                else:
                    ''' compilation is disabled for this workflow. presumably something else will generate it dynamically, later. '''
                    fileName = "%s.dax" % element.getLabel ()
                    self.getReplicaCatalog().addEntry (fileName,
                                                       "file://%s/%s" % (self.getOutputDir (), fileName),
                                                       "local")

    def ast_mapEdges (self):
        """ Map edges. Add all graph edges to the object map if theyre not already there. """
        logger.debug ("ast:map-edges: cid=%s", self.compilerId)		
        edgeElements = []
        edges = self.graph.getEdges ()
        for edge in edges:
            element = self.getElement (edge.getId ())
            if not element:
                element = self.ast_mapEdge (edge)
            edgeElements.append (element)
        return edgeElements

    def ast_mapEdge (self, edge):
        """ Add an edge to the object map. """
        element = ASTElement (edge)
        logger.debug ("ast:map-edge (%s)->(%s)", edge.getSource(), edge.getTarget ())
        self.addElement (edge.getId (), element)
        return element
    
    def ast_dereference (self): 
        """Dereference: lookup concrete objects and alter the graph to remove references. """
        logger.debug ("ast:dereference: cid=%s", self.compilerId)
        nodes = self.graph.getNodes ()
        for node in nodes:
            refId = node.getId ()
            element = self.getElement (node.getId ())
            if element:
                nodeId = element.getId ()
                if refId != nodeId: 
                    ''' node is a reference '''
                    edges = self.graph.getEdges ()
                    for edge in edges:
                        if edge.getTarget () == refId:
                            ''' for every edge pointing to the reference '''
                            edge.setTarget (nodeId)
                        if edge.getSource () == refId:
                            ''' for every edge from the reference '''
                            edge.setSource (nodeId)

    def ast_inherit (self):
        """ Inherit: propagate properties from base to derived objects. """
        logger.debug ("ast:inheritance: cid=%s", self.compilerId)
        abstractElements = self.getElementsByType (self.ABSTRACT)
        for abstractElement in abstractElements:
            self.ast_inheritAbstractElement (abstractElement)

    def ast_inheritAbstractElement (self, abstractElement):
        isRoot = True
        origins = abstractElement.getOrigins (self.graph)
        for origin in origins:
            originElement = self.getElement (origin)
            if originElement and originElement.getType () == self.ABSTRACT:
                isRoot = False
                break
        if isRoot:
            self.ast_effectInheritance (abstractElement)

    def getAbstractRootElements (self, abstractElement):
        roots = []
        origins = abstractElement.getOrigins (self.graph)
        for origin in origins:
            originElement = self.getElement (origin)
            if originElement and originElement.getType () == self.ABSTRACT:
                origins = self.getAbstractRootElements (originElement)
                if len (origins) == 0:
                    roots.append (o)
                else:
                    for o in origins:
                        if not o in roots:
                            roots.append (o)
        return roots

    def ast_effectInheritance (self, abstractElement, tab=""):        
        """ Effect Inheritance: Add inherited characteristics to targeted nodes. """
        logger.debug ("%sast:inherit:%s", tab, abstractElement.getLabel ())
        targets = abstractElement.getTargets (self.graph)
        logger.debug ("ast-inherit-abstract: %s", abstractElement.getNode().getType ())
        for targetId in targets:
            target = self.getElement (targetId, regex=True)
            if target:
                if isinstance (target, list):
                    for item in target:
                        self.ast_addAncestor (item, abstractElement, tab, recurse=False)
                else:
                    self.ast_addAncestor (target, abstractElement, tab)

    def ast_addAncestor (self, target, ancestor, tab="", recurse=True):
        logger.debug ("%s-ast:inherit:target: parent=(id=%s,label=%s) target=(id=%s,label=%s)",
                      tab, ancestor.getId (), ancestor.getLabel (), target.getId (), target.getLabel ())
        target.addAncestor (ancestor)
        logger.debug ("object %s after inheriting %s\n%s",
                      target.getLabel (),
                      ancestor.getLabel (),
                      json.dumps (target.getProperties (), indent=3, sort_keys=True))
        if target.getType () == self.ABSTRACT and recurse:
            self.ast_effectInheritance (target, "%s%s" % (tab, "    "))

    def ast_processEdgeOperators (self, edgeElements):
        """ Process edge operators. """
        result = []
        for edge in edgeElements:
            deleteOperator = edge.get ("deleteWhenSource") # TODO: 1. make a constant 2. document.
            if deleteOperator:
                source = self.getElement (edge.getNode().getSource ())
                match = re.match (deleteOperator, source.getLabel ())
                if not match:
                    logger.debug ("ast:edge-ops: %s did not match delete operator [%s]", source.getLabel (), deleteOperator)
                    result.append (edge)
                else:
                    logger.debug ("ast:edge-ops: %s matched delete operator [%s]", source.getLabel (), deleteOperator)
            else:
                result.append (edge)
        return result

    def buildAST (self):
        """ build the abstract syntax tree """
        logger.debug ("ast:build-abstractsyntax: cid=%s", self.compilerId)
        self.ast_mapEdges ()
        jobs = self.ast_mapNodes ()
        if not self.isContextModel ():
            edgeElements = self.ast_processEdgeOperators (self.ast_mapEdges ())
            self.ast_dereference ()
            self.ast_inherit ()

            self.validateGraph ()

            daxContext = self.ast_analyzeJobs (jobs, edgeElements)
            self.ast_createDependencies (daxContext)
            self.reportErrors ()

    def ast_analyzeJobs (self, jobs, edgeElements):
        """ Analyze Jobs: Grok inputs and outputs of each job. """
        daxContext = ASTContext ()
        for job in jobs:
            logger.debug ("consideringjob: %s", job.getLabel ())
            jobId = job.getNode().getId ()
            jobLabel = job.getNode().getLabel ()
            logger.debug ("ast-analyze-job: job=%s, id=%s, cid=%s", jobLabel, jobId, self.compilerId)
            jobContext = JobContext (job, self.namespace, self.version)
            for edge in edgeElements:
                edgeTarget = edge.getNode().getTarget ()
                source = self.getElement (edge.getNode().getSource ())
                ''' an output file can be the target end of an edge from a job '''
                if source and source.getId () == jobId:
                    target = self.getElement (edgeTarget)
                    if target:
                        logger.debug ("---thing: %s", target.getLabel ())
                        if target.getType () == self.FILE:
                            self.addOutputFile (jobContext, target, edge)
                            logger.debug ("add-job-output: (cid=%s) job (%s) outputs (%s)", self.compilerId, job.getLabel (), target.getLabel ())

                elif edgeTarget == jobId and source:
                    logger.debug ("add-job-edge: source(%s,%s)-edge(%s)->target(%s,%s)",
                                   source.getId (), source.getLabel (), edge.getId (), job.getId (), job.getLabel ())
                    # some file, executable or other modifier to a job.
                    sourceType = source.getType ()
                    # an executable can be the source end of an edge to a job  
                    if sourceType == self.EXECUTABLE:
                        self.addExecutable (jobContext, source)

                    # a file pointing to a job is an input file
                    elif source.getType () == self.FILE:
                        self.addInputFile (jobContext, source, edge)
                        target = self.getElement (edgeTarget)
                        logger.debug ("addingfile %s %s", source.getLabel (), target.getLabel ())

                    # an abstract job can be the source end of an edge to a job 
                    elif sourceType == self.JOB or sourceType == self.WORKFLOW or sourceType == self.DAX:
                        jobContext.addOrigin (source.getId ())
                        logger.debug ("job-dependency: %s is origin of %s (cid=%s)", source.getLabel (), job.getLabel (), self.compilerId)

                        # TODO: Only if it's not already in the replica catalog ...
                        if sourceType == self.DAX:
                            basename = "%s.dax" % source.getLabel ()
                            fileAbsolutePath = os.path.abspath (os.path.join (self.getOutputDir (), basename))
                            if not os.path.exists (fileAbsolutePath):
                                #GraysonUtil.writeFile (fileAbsolutePath, "");
                                fileURL = "file://%s" % fileAbsolutePath
                                self.getReplicaCatalog().addEntry (basename, fileURL, self.ATTR_LOCAL)
            self.ast_translateToOutputModel (jobContext, daxContext)
        return daxContext

    def ast_translateToOutputModel (self, jobContext, daxContext):
        """ Translate To Output Model: Write a job into the workflow management systems workflow model. """
        job = jobContext.getJob ()
        jobId = job.getId ()
        abstractJob = None
        jobType = job.getType ()
        logger.debug ("job (%s) type is (%s)", job.getLabel (), job.getType ())
        if jobType == self.WORKFLOW or jobType == self.DAX:
            logger.debug ("emitter:add-workflow-job: %s", job.getLabel ())
            abstractJob = self.workflowModel.addSubWorkflow (self.formWorkflowName (job))
            if jobId in self.compilerId:
                pass
            else:
                logger.debug ("emitter:add-workflow:test: Unable to create test job for workflow: %s", job.getLabel ())
        elif jobType == self.JOB:
            logger.debug ("emitter:add-job: %s", job.getLabel ())
            abstractJob = self.workflowModel.addJob (job.getId ())
        if abstractJob:
            job.setDaxNode (abstractJob)
            self.workflowModel.addProfiles (abstractJob, job.getProfiles ())
            self.workflowModel.addInputFiles (abstractJob, jobContext.inFiles)
            self.workflowModel.addOutputFiles (abstractJob, jobContext.outFiles)
            args = job.get (self.ATTR_ARGS)
            if type (args) == list:
                args = " ".join (args)
            if args:
                allFiles = copy (jobContext.inFiles)
                allFiles.update (jobContext.outFiles)
                eachArg = args.split (" ")
                for arg in eachArg:
                    if arg in allFiles:
                        logger.debug ("emitter:replace-filename: %s", arg) 
                        self.workflowModel.addArguments (abstractJob, allFiles [arg][0].getDaxNode ())
                    else:
                        self.workflowModel.addArguments (abstractJob, arg)
            daxContext.addWmsJob (jobId, abstractJob)
            daxContext.setDependencies (jobId, jobContext.getOrigins ())
        return daxContext

    def writeDAX (self, stream=sys.stdout):
        """ Write compiler output for this compiler instances workflow model to the provided stream. """
        if len(self.errorMessages) == 0 and not self.isPackaging ():
            logger.debug ("compiler:write-output: cid=%s", self.compilerId)
            self.workflowModel.writeExecutable (stream)

    def getExecuteArguments (self, workflow=None, other=[]):
        """ Get arguments to execute this workflow on the configured workflow management system. """
        return self.getWorkflowManagementSystem().getExecuteArguments (self.getSites (),
                                                                       workflow,
                                                                       other)

    def replaceProps (self, obj):
        value = obj
        if isinstance (obj, basestring):
            value = self.ast_replaceProperties (obj)
        elif isinstance (obj, dict):
            value = {}
            for k in obj:
                value [k] = self.replaceProps (obj [k]) 
        return value


    def addSite (self, clusterId, site, entry):
        logger.debug ("site: %s", json.dumps (site, indent=3, sort_keys=True))
        if not clusterId in self.getSites ():
            self.setSites (",".join ([ self.getSites (), clusterId ]))
        logger.debug ("ast:add-site: %s", self.getSites ())
        self.getSiteCatalog ().addEntry (clusterId, entry)

    def configureSites (self):
        """ Generate workflow management system specific catalogs. """
        site = self.getProperty ("site")

        logger.debug ("configuring site: %s", json.dumps (site, sort_keys=True, indent=3))
        if site:
            ''' site catalog '''

            site = self.replaceProps (site)

            if "CLUSTER_ID" in site:
                clusterId = site ["CLUSTER_ID"]
                entry = {
                    "siteName"                     : clusterId,
                    "hostName"                     : site ["CLUSTER_HOSTNAME"],
                    "scheduler"                    : site ["CLUSTER_SCHEDULER"],
                    "schedulerType"                : "unknown",
                    "scratchFileServerProtocol"    : "gsiftp",
                    "scratchFileServerURL"         : "gsiftp://%s" % site ["CLUSTER_HOSTNAME"],
                    "scratchFileServerMountPoint"  : site ["CLUSTER_WORK_DIR"],
                    "scratchInternalMountPoint"    : site ["CLUSTER_WORK_DIR"],
                    "storageFileServerProtocol"    : "gsiftp",
                    "storageFileServerMountPoint"  : site ["CLUSTER_WORK_DIR"],
                    "storageMountPoint"            : site ["CLUSTER_HOSTNAME"],
                    "storageInternalMountPoint"    : site ["CLUSTER_WORK_DIR"],
                    "pegasusLocation"              : site ["CLUSTER_PEGASUS_HOME"],
                    "globusLocation"               : site ["CLUSTER_GLOBUS_LOCATION"]
                    }
                self.addSite (clusterId, site, entry)
            elif "clusterId" in site:
                clusterId = site ["clusterId"]
                self.addSite (clusterId, site, site)
            else:
                raise ValueError ("Either clusterId nor CLUSTER_ID must be defined in the site element: (%)" % str(site))

        sites = self.getProperty ('sites')
        if sites:
            logger.debug ("site: %s", sites)
            for key in sites.iterkeys ():
                logger.debug ("site:key: %s", key)
                original = self.getSiteCatalog().getEntry (key)
                if original:
                    logger.debug ("site:original: %s", json.dumps (original, indent=4))
                    site = sites [key]
                    if site:
                        for k in site.iterkeys ():
                            site [k] = self.ast_replaceProperties (site [k])
                        original.update (site)
                        logger.debug ("site:site: %s", site)
                        logger.debug ("site:updated: %s", json.dumps (original, indent=4))

    def generateCatalogs (self, write=True):
        if write:
            self.writeMetaDataCatalogs ()

    def getContextualizedModels (self):
        allModels = self.getAllModelPaths ()
        contextualizedMap = {}
        for model in allModels:
            logger.debug ("   contextualizing model: %s", model)
            logicalName = os.path.realpath (model)
            tempLogicalName = logicalName
            modelPath = self.getModelPath ()
            last = None
            for element in modelPath:
                element = os.path.realpath (element)
                logger.debug ("last: %s, element: %s, logical: %s", last, element, logicalName)
                if not last or len(last) < len(element):
                    if logicalName.startswith (element):
                        tempLogicalName = logicalName.replace (element, "")
                        logger.debug ("       temp logical: %s", tempLogicalName)
                        last = element
            contextualizedMap [tempLogicalName] = model
        return contextualizedMap

    def mapModelRelationships (self):
        """ Map model relationships. """
        self.ast_mapNodes ()
        compilerId = self.compilerId
        elements = self.getElementsByType (self.WORKFLOW)
        seen = []
        for element in elements:
            if not element.getLabel () in seen:
                seen.append (element.getLabel ())
                logger.debug ("ast:map-model-relationships: register job: %s", element.getLabel ())
                self.ast_compileWorkflow (element)
        self.compilerId = compilerId

    def package (self, additionalFiles):
        """ Analyze and package a Grayson configuration with all accompanying context models into a compressed archive. """

        ''' map '''
        self.mapModelRelationships ()
            
        self.configureSites ()
        self.generateCatalogs (write=False)        

        logger.debug ("myid: %s %s", self.compilerId, self.getSites ())

        outputArchive = os.path.basename (self.compilerId)
        outputArchive = outputArchive.replace (self.MODEL_SUFFIX, "grayson")
        outputArchive = os.path.join (self.getOutputDir (), outputArchive)

        contextualizedMap = self.getContextualizedModels ()

        ''' write context info '''
        conf = {
            self.CONF_INPUT_PROPERTIES : self.getInputModelProperties (),
            self.CONF_OUTPUT_FILE : self.output,
            self.CONF_SITES : self.getSites ()
            }
        GraysonUtil.writeFile (self.CONF_FILE, json.dumps (conf, indent=4))
        contextualizedMap [self.CONF_FILE] = os.path.join (".", self.CONF_FILE)

        GraysonUtil.listDirs (additionalFiles, contextualizedMap)

        ''' package '''
        GraysonPackager.package (patterns = contextualizedMap,
                                 output_file = outputArchive,
                                 relativeTo = os.getcwd ())
        ''' verify package '''
        GraysonPackager.verify (input_file = outputArchive)


    def unpack (self, archive, outputdir):
        """ Unpack an archive. """

        unpackdir = os.path.join (outputdir, "%s.tmp" % archive)
        unpackdir = os.path.join (outputdir)

        ''' verify package '''
        GraysonPackager.verify (input_file = archive)
        ''' unpack '''
        GraysonPackager.unpack (input_file = archive, output_dir = unpackdir)


        bin = os.path.join (unpackdir, "bin")
        if os.path.isdir (bin):
            os.system ("chmod +x %s/*" % bin)
            logger.debug ("chmodding bin")

        logger.debug ("unpacked archive: %s", archive)

        ''' load the config object '''
        confFile = os.path.join (unpackdir, self.CONF_FILE)
        if os.path.exists (confFile):
            data = GraysonUtil.readFile (confFile)
            config = json.loads (data)
            logger.debug ("compiler:unpack:load-conf: (%s)", config)
            if self.CONF_INPUT_PROPERTIES in config:
                self.setInputModelProperties (config [self.CONF_INPUT_PROPERTIES])
                logger.debug ("grayson:conf:set-input model properties: %s", self.getInputModelProperties ())
            if self.CONF_OUTPUT_FILE in config:
                self.output = config [self.CONF_OUTPUT_FILE]
                logger.debug ("grayson:conf:set-output: %s", self.output)
            if self.CONF_SITES in config:
                self.setSites (config [self.CONF_SITES])
                logger.debug ("grayson:conf:set-sites: %s", self.output)
        else:
            raise GraysonCompilerException ("%s is not a correctly formatted grayson archive.")

        baseModelName = os.path.basename (archive).replace ("grayson", self.MODEL_SUFFIX)
        match = re.search (".*(_[0-9]+).%s" % self.MODEL_SUFFIX, baseModelName)
        if match:
            baseModelName = baseModelName.replace (match.group (1), "")
            logger.debug ("grayson:base-model-name: %s", baseModelName)
        return (unpackdir, os.path.join (unpackdir, baseModelName))

    #////////////////////////////////////////////////////////////
    #{ 9.0 Static API
    #////////////////////////////////////////////////////////////
    @staticmethod
    def compile (models=[],
                 output=sys.stdout,
                 modelPath=None, #[".","model"],
                 namespace="app",
                 version="1.0",
                 logLevel=None,
                 logDir=None,
                 appHome=None,
                 clean=False,
                 outputdir=".",
                 modelProperties={},
                 execute=False,
                 sites="local",
                 toLogFile=None,
                 packaging=False,
                 packagingAdditionalFiles = [],
                 plugin=CompilerPlugin ()):

        """ Compile the given input models to create an executable workflow. """

        ''' initialize output directory '''
        if not os.path.exists (outputdir):
            os.makedirs (outputdir)
        if not appHome:
            appHome = os.getcwd ()
        logger.debug ("apphome: %s", appHome)

        ''' initialize logging '''
        logManager = LogManager.getInstance (logLevel, logDir, toFile=toLogFile)
        fileHandler = logManager.getFileHandler ()
        if fileHandler:
            logger.addHandler (fileHandler)

        ''' initialize compiler '''
        compiler = GraysonCompiler (namespace   = namespace,
                                    version     = version,
                                    logManager  = logManager,
                                    clean       = clean,
                                    appHome     = appHome,
                                    outputDir   = outputdir)
        compiler.output = output
        if type(output) == file:
            compiler.output = "stdout"
        compiler.setSites (sites)        
        compiler.setPackaging (packaging)
        if modelProperties:
            compiler.setInputModelProperties (modelProperties)
        compiler.setCompilerPlugin (plugin)

        modelName = models [0]
        if not modelPath:
            modelPath = []

        ''' unpack if its an archive '''
        unpackdir = None
        if modelName.endswith (".grayson"):
            fileName = os.path.basename (modelName)
            (unpackdir, newName) = compiler.unpack (modelName, outputdir)

            compiler.appHome = unpackdir
            compiler.getWorkflowManagementSystem().getSiteCatalog().configureLocal ()
            local = compiler.getWorkflowManagementSystem().getSiteCatalog().getEntry ("local")

            localStorage = "%s/work/outputs" % compiler.appHome
	    local ["scratchFileServerMountPoint"] = localStorage
            local ["scratchInternalMountPoint"]   = localStorage
            local ["storageFileServerMountPoint"] = localStorage
            local ["storageInternalMountPoint"]   = localStorage

            models.remove (modelName)
            models.insert (0, newName)
            modelName = newName
            logger.debug ("adding unpack model path: %s", os.path.dirname (newName)) 
            modelPath.append (os.path.dirname (newName))

        ''' initialize model path '''
        if os.path.sep in modelName and not modelName.endswith (".grayson"):
            modelPath.append (os.path.dirname (modelName))
        if modelPath:
            compiler.setModelPath (modelPath)

        ''' load graphs, build abstract syntax and workflow model '''
        logger.info ("Grayson - Compiling models:")
        for model in models:
            logger.info ("   model: %s", model)
        compiler.parse (models)
        compiler.setTopModel (models [0])
        compiler.buildAST ()

        ''' write output workflow '''
        if not compiler.isContextModel () and not packaging:
            try:
                opened_output = False
                if isinstance (output, str):
                    output = open (os.path.join (outputdir, output), "w")
                    opened_output = True
                try:
                    ''' generate executables '''
                    compiler.writeDAX (output)

                    compiler.getCompilerPlugin().notifyWorkflowCreation (modelName, output, topWorkflow=True)
                finally:
                    if opened_output:
                        output.close ()
            except IOError:
                traceback.print_stack ()

        if packaging:

            ''' package '''
            compiler.package (packagingAdditionalFiles)

        else:
            ''' generate meta data catalogs '''
            compiler.generateCatalogs ()
            
            ''' execute the workflow '''
            if execute:
                workflowName = os.path.join (outputdir, compiler.output)
                compiler.getWorkflowManagementSystem().executeWorkflow (compiler.getSites (),
                                                                        workflowName,
                                                                        plugin)

        return compiler
