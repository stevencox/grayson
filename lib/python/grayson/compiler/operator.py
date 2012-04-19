import os
import shutil
import tarfile
import logging

from string import Template
from grayson.common.util import GraysonUtil

logger = logging.getLogger (__name__)

class Operator (object):
    def __init__(self, name):
        self.name = name
    def execute (self, context={}):
        pass
    def validate (self, context):
        return context

class DynamicMapOperator (Operator):
    def __init__(self):
        super (DynamicMapOperator, self).__init__("dynamicMap")
        self.version = "1.0"
        self.header = """<?xml version='1.0' encoding='UTF-8'?>
<!-- generator: grayson -->
<adag xmlns='http://pegasus.isi.edu/schema/DAX'
      xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'
      xsi:schemaLocation='http://pegasus.isi.edu/schema/DAX http://pegasus.isi.edu/schema/dax-3.2.xsd'
      version='3.2'
      name='${namespace}'>
"""
        self.footer = """
</adag>"""

        self.subdax = """
<dax id='${namespace}_$c' file='$outputname' >
   <argument>--force</argument>
</dax>"""


    def validate (self, context):
        return context

    def execute (self, context={}):

        operatorContext = context ['operator']

        method         = operatorContext ["method"]
        inputFile      = operatorContext ["input"]
        variable       = operatorContext ["variable"]
        index          = operatorContext ["index"]
        flow           = operatorContext ["flow"]

        outputBasename = context ["outputName"]
        modelPath      = context ["modelPath"]
        outputDir      = context ["outputDir"]
        contextModels  = context ["contextModels"]
        sites          = context ["sites"]
        appHome        = context ["appHome"]
        graysonHome    = context ["graysonHome"]
         
        tmpOutputDir = os.path.join (outputDir, "tmp") # avoid overwriting replica catalog.

        contextModels = contextModels.split (os.pathsep)
        models = [ flow ]
        for model in contextModels:
            models.append (model)
        
        main_flow_name = os.path.join (outputDir, "%s.dax" % flow.replace (".graphml", ""))
        namespace = flow.replace (".graphml", "")

        flowContext = { "namespace" : flow }
        template = Template (self.header)

        text = [ template.substitute (flowContext) ]

	replicaText = []
        
        tar = tarfile.open (inputFile, "r:gz")
        members = tar.getmembers ()

        c = 0
        for archiveMember in members:
            outputname = "%s.%s.dax" % ( outputBasename, c)
            define = {
                variable  : archiveMember.name,
                index     : c,
                "appHome" : appHome
                }
            GraysonCompiler.compile (models          = models,
                                     output          = outputname,
                                     modelPath       = modelPath,
                                     namespace       = namespace,
                                     version         = version,
                                     modelProperties = definitions,
                                     outputdir       = tmpOutputDir,
                                     sites           = sites,
                                     logLevel        = "debug",
                                     toLogFile       = os.path.join (outputDir, "%s-log.txt" % flow))
            replicaText.append ('%s file://%s/%s pool="local"'  %s (outputname, outputDir, outputname))
            template = Template (self.subdax)
            flowContext ["c"] = c
            text.append (template.substitute (flowContext))
            c += 1

            raise ValueError ("hi")
                        
        text.append (footer)

        shutil.move ( src = os.path.join (tmpOutputDir, outputname),
                      dst = os.path.join (outputDir, outputname))

        GraysonUtil.writeFile (outputPath = main_flow_name,
                               data       = os.path.join (outputDir, '\n'.join (text)))

        replicaText.append ('%s file://%s pool="local"' % (main_flow_name, main_flow_name))
        masterRC = os.path.join (outputDir, "replica-catalog.rc")
        GraysonUtil.concatenateFiles (A = os.path.join (tmpOutputDir, "replica-catalog.rc"),
                                      B = masterRC,
                                      outputName = masterRC)

        go = """
cp $PEGASUS_HOME/bin/pegasus-plan /tmp
"""
        os.system (go)

class OperatorContext (object):
    def __init__(self, compiler):
        self.compiler = compiler

class OperatorRegistry (object):
    def __init__(self, operatorTypes):
        self.registry = {}
        for operatorType in operatorTypes:
            operator = operatorType ()
            if isinstance (operator, Operator):
                self.register (operator)

    def register (self, operator):
        self.registry [operator.name] = operator

    def execute (self, operatorName, context):
        operator = self.registry [operatorName]
        context = operator.validate (context)
        if context:
            operator.execute (context)
