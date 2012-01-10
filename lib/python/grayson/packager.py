
''' system '''
import logging
import os
import string
import shutil
import sys
import time
import zipfile
import glob
from grayson.log import LogManager

class GraysonPackager:
    def __init__(self):
        self.logger = logging.getLogger ()

    def write (self, patterns, output_file=None, relativeTo=None):
        logging.info ("** grayson:create-archive: (%s)", output_file)
        try:
            output = sys.stdout
            if output_file:
                output = open (output_file, "w")
            zip_file = zipfile.ZipFile (output, "w")
            try:
                if type (patterns) == list:
                    file_list = []
                    for pattern in patterns:
                        for name in glob.glob (pattern):
                            file_list.append (name)
                    for file_name in file_list:
                        if relativeTo:
                            archiveFileName = file_name.replace (relativeTo, "")
                        else:
                            archiveFileName = os.path.basename (file_name)
                    logging.debug ("  --write (%s)", archiveFileName)
                    zip_file.write (file_name, archiveFileName, zipfile.ZIP_DEFLATED)
                elif type (patterns) == dict:
                    for archiveFileName in patterns:
                        physicalLocation = patterns [archiveFileName]
                        logging.debug ("  --write %40s pfn: %s", archiveFileName, physicalLocation)
                        zip_file.write (physicalLocation, archiveFileName, zipfile.ZIP_DEFLATED)                        
            finally:
                zip_file.close () #closes underlying output
        except IOError:
            self.logger.exception ("io error occurred writing %s", output)
        self.logger.debug ("wrote model archive: %s" % output.name)

    def verifyArchive (self, input_file):
        logging.info ("** grayson:verify-archive: (%s)", input_file)
        try:
            zip_file = zipfile.ZipFile (file=input_file,
                                        mode="r",
                                        compression=zipfile.ZIP_DEFLATED)            
            try:                
                zip_file.testzip ()
                self.logger.info ("%-50s %-30s %-5s %-5s %-5s", "File Name", "Date", "Size", "Comp", "%")
                self.logger.info ("%-50s %-30s %-5s %-5s %-5s", "=========", "====", "====", "====", "====")
                for info in zip_file.infolist ():
                    percent = 100
                    if info.file_size > 0:
                        percent = round ((float(info.compress_size) / float(info.file_size)) * 100, 2)
                    self.logger.info ("%-50s %-30s %-5s %-5s %-5s", info.filename, info.date_time, info.file_size, info.compress_size, percent)
                                      
            finally:
                zip_file.close ()
        except IOError:
            self.logger.exception ("io error occurred writing %s", zip_file)
        self.logger.debug ("verified model archive: %s" % input_file)            


    def unpackArchive (self, input_file, output_dir="."):
        self.logger.info ("** grayson:unpack-archive: (%s) to directory: (%s)",
                          input_file,
                          output_dir)
        try:
            zip_file = zipfile.ZipFile (file=input_file,
                                        mode="r",
                                        compression=zipfile.ZIP_DEFLATED)
            try:
                '''
                if not os.path.exists (output_dir):
                    os.makedirs (output_dir)                
                    '''
                for info in zip_file.infolist ():
                    self.logger.info ("  file: %-40s date: %s bytes: %s zipped: %s", info.filename, info.date_time, info.file_size, info.compress_size)
                zip_file.extractall (output_dir)
            finally:
                zip_file.close ()
        except IOError:
            self.logger.exception ("io error occurred unpacking %s", input_file)
        self.logger.debug ("unpack for archive: %s", input_file)

    @staticmethod
    def getPackager (logLevel=None, logDir=None):
        #LogManager.getInstance (logLevel, logDir)
        return GraysonPackager ()

    @staticmethod
    def package (patterns, output_file, logLevel=None, relativeTo=None):
        GraysonPackager.getPackager(logLevel).write (patterns, output_file, relativeTo)

    @staticmethod
    def verify (input_file, logLevel=None):
        GraysonPackager.getPackager(logLevel).verifyArchive (input_file)

    @staticmethod
    def unpack (input_file, output_dir, logLevel=None, logDir=None):
        GraysonPackager.getPackager(logLevel, logDir).unpackArchive (input_file, output_dir)


def test_grayson_packager ():

    log_level = None

    output_dir = "test-output"
    if not os.path.exists (output_dir):
        os.makedirs (output_dir)

    model_patterns = os.path.join ("model", "*.graphml")
    output_file = os.path.join (output_dir, "test-archive.zip")
    GraysonPackager.package (patterns = [ model_patterns ],
                             output_file = output_file,
                             logLevel = log_level)

    GraysonPackager.verify (input_file = output_file,
                            logLevel = log_level) 

    unpack_output_dir = os.path.join (output_dir, "unpack")
    GraysonPackager.unpack (input_file = output_file,
                            output_dir = unpack_output_dir,
                            logLevel = log_level) 

    shutil.rmtree (output_dir)
    
if __name__ == '__main__':
    test_grayson_packager ()

__all__ = [ "GraysonPackager" ]

