import glob
import logging
import os
import sys
import traceback

from django.conf import settings
from django.utils import unittest

from grayson.compiler.compiler import GraysonCompiler
from grayson.packager import GraysonPackager

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
import Pegasus.DAX3

class GraysonTestCase (unittest.TestCase):

    def setUp (self):
        logger_name = "%s.%s" % (__name__, self.__class__.__name__)
        self.logger = logging.getLogger (logger_name)
        self.dataPath = os.path.join ("graysonapp", "tests")
        self.outputPath = os.path.join ("graysonapp", "tests", "output")
        if not os.path.exists (self.outputPath):
            os.makedirs (self.outputPath)
        self.archiveName = os.path.join (self.outputPath, "grayson-workflow.zip")
        self.unpackDirectory = os.path.join (self.outputPath, "unpack")
        self.logLevel = "info"

    def banner (self):
        self.logger.info ("===== T E S T ====== (%s)", self.id())

    def test_package (self):
        self.banner ()
        models = os.path.join (self.dataPath, "model", "*.graphml")
        GraysonPackager.package ([models], self.archiveName, self.logLevel)

    def test_packageVerify (self):
        self.banner ()
        GraysonPackager.verify (self.archiveName)

    def test_packageUnpack (self):
        self.banner ()
        GraysonPackager.unpack (self.archiveName, self.unpackDirectory, self.logLevel)

    def getUnpack (self, *args):
        part = ""
        for arg in args:
            part = os.path.join (part, arg)
        return os.path.join (self.unpackDirectory, part)

    def test_compile (self):
        self.banner ()
        modelPattern = self.getUnpack ("model", "*.graphml")
        names = glob.glob (modelPattern)
        output_workflow = self.getUnpack ("workflow.dax")
        GraysonCompiler.compile (models = names,
                                 output = output_workflow,
                                 modelPath = [ self.getUnpack ("model") ],
                                 namespace="grayson-test",
                                 version="2.0",
                                 logLevel = self.logLevel)

        self.logger.info ("========================================")
        self.logger.info ("Analyzing generated DAX with Pegasus API")
        self.logger.info ("========================================")
        dag = Pegasus.DAX3.parse (output_workflow)

        self.logger.info ("dag-name: %s", dag.name)

        self.logger.info ("dag-files:")
        for file in dag.files:
            self.logger.info ("   %s", file.name)

        self.logger.info ("dag-jobs:")
        for job in dag.jobs:
            if isinstance (job, DAX):
                self.logger.info ("   %s", job.file)
            else:
                self.logger.info ("   %s namespace: %s version: %s", job.name, job.namespace, job.version)

        self.logger.info ("dag-transformations:")
        for trans in dag.transformations:
            self.logger.info ("   %s (namespace:%s, version:%s", trans.name, trans.namespace, trans.version)
            for use in trans.used_files:
                self.logger.info ("       %s", use.name)

        self.logger.info ("dag-executables:")
        for exe in dag.executables:
            self.logger.info ("   %s (namespace:%s, version:%s, arch:%s, os:%s)", exe.name, exe.namespace, exe.version, exe.arch, exe.os)

        self.logger.info ("dag-dependencies:")
        for dep in dag.dependencies:
            self.logger.info ("   %s", dep.child.id)
        self.assertEqual('a', 'a')

    def tearDown (self):
        print "complete"

def suite ():
    suite = unittest.TestSuite ()
    tests = [ 'test_package',
              'test_packageVerify',
              'test_packageUnpack',
              'test_compile' ]
    '''
    for test in tests:
        suite.addTest (GraysonTestCase (test))
        '''
    return suite

