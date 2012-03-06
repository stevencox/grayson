import os
import json
import re
import logging
import traceback

logger = logging.getLogger (__name__)

class GraysonUtil (object):
    
    WORKFLOW_QUEUE = 'workflow'

    @staticmethod
    def form_workdir_path (unpackDir, username, workflowId, runId=""):
        return os.path.join (unpackDir, "work", username, "pegasus", workflowId, runId)
    
    @staticmethod
    def getPegasusHome ():
        pegasusLocation = unicode (os.getenv ("PEGASUS_HOME"))
        if not pegasusLocation:
            raise ValueError ("PEGASUS_HOME must be defined")
        return pegasusLocation

    @staticmethod
    def containsAny (string, items):
        result = False
        for item in items:
            if item in string:
                result = True
                break
        return result

    @staticmethod
    def writeFile (outputPath, data):
        aFile = open (outputPath, "w")
        aFile.write (data)
        aFile.close ()

    @staticmethod
    def readFile (inputPath, process=None):
        result = []
        file = None

        def defaultProcess (line):
            result.append (line)

        if not process:
            process = defaultProcess

        try:
            try:
                file = open (inputPath)
                for line in file:
                    process (line)
            except IOError as e:
                traceback.print_exc ()
        finally:
            if file:
                file.close ()
        return "".join (result)

    @staticmethod
    def concatenateFiles (A, B, outputName, separator="\n"):
        A = GraysonUtil.readFileAsString (A)
        B = GraysonUtil.readFileAsString (B)
        GraysonUtil.writeFile (outputName, "%s%s%s" % (A, separator, B))

    @staticmethod
    def readFileAsString (fileName):
        stream = None
        result = ""
        text = []
        try:
            try:
                stream = open (fileName, 'r')
                for line in stream:
                    text.append (line)
            except IOError, e:
                traceback.print_exc ()
        finally:
            if stream:
                stream.close ()
        if len (text) > 0:
            result = "".join (text)
        return result

    @staticmethod
    def readJSONFile (inputPath):
        return json.loads (GraysonUtil.readFile (inputPath))

    @staticmethod
    def listDirs (files, collection):
        def nodot(item): return item[0] != '.'
        for item in files:
            if os.path.isdir (item):
                directories = [ item ]
                while len(directories)>0:
                    directory = directories.pop()
                    contents = filter (nodot, os.listdir(directory))
                    for name in contents:
                        fullpath = os.path.join(directory,name)
                        if os.path.isfile(fullpath):
                            collection [fullpath] = fullpath
                        elif os.path.isdir(fullpath):
                            directories.append(fullpath)  
            else:
                collection [item] = item

    @staticmethod
    def getDirs (of_dir):
        result = []
        def nodot(item): return item[0] != '.'
        if (os.path.isdir (of_dir)):
            contents = filter (nodot, os.listdir (of_dir))
            for item in contents:
                path = os.path.join (of_dir, item)
                if os.path.isdir (path):
                    result.append (path)
        return result

    @staticmethod
    def getFiles (the_dir, recursive=True):
        logger.debug ( "util:getfiles: %s",  the_dir )
        outputfiles = []
        for root, dirs, files in os.walk (the_dir, topdown=(not recursive)):            
            for f in files:
                fullpath = os.path.join (root, f)
                outputfiles.append (fullpath)
            for d in dirs: 
                fullpath = os.path.join (root, d)
                outputfiles.append (fullpath)
                if not recursive:
                    dirs.remove (d)
        return outputfiles

    @staticmethod
    def findFilesByName (text, files):
        logger.debug ("--: text: %s", text)
        pattern = re.compile (text)
        output = []
        for file in files:
            if pattern.search (file):
                output.append (file)
            else:
                pass
        return output

    @staticmethod
    def getUserRelativePath (path, username):
        result = path
        end = "".join ( [ os.path.sep, username, os.path.sep ] )
        if end in path:
            result = path [  path.rfind (end) + len (end) : ]
        return result

    @staticmethod
    def relativize (object, keys, username):
        for key in keys:
            if key in object:
                value = object [key]
                if username in value:
                    object [key] = GraysonUtil.getUserRelativePath (value, username)
        return object

    @staticmethod
    def getPattern (pattern, text, group=1):
        result = None
        match = re.search (pattern, text)
        if match:
            result = match.group (group)
        return result

    @staticmethod
    def getPrecompiledPattern (pattern, text, group=1):
        result = None
        match = pattern.search (text)
        if match:
            result = match.group (group)
        return result

    @staticmethod
    def ceilingString (value, maxLength=140, fromEnd=False):
        return value [ len (value) - maxLength - 1 : len (value) - 1 ] if fromEnd else value [ 0 : maxLength ]
