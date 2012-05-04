
''' system '''
import logging
import logging.handlers
import os
import sys

class LogManager:
    theInstance = None
    def __init__(self, logLevel="info", logDir=None, toFile=None):
        self.loggingLevel = logLevel
        if logDir:
            self.logDirectory = logDir
        else:
            self.logDirectory = "logs"
        self.logLevels = {
            'debug'    : logging.DEBUG,
            'info'     : logging.INFO,
            'warning'  : logging.WARNING,
            'error'    : logging.ERROR,
            'critical' : logging.CRITICAL
            }
        level = self.logLevels [self.loggingLevel]
        self.fileHandler = None

        handler = logging.StreamHandler (sys.stdout)
        if toFile:
            if not os.path.exists (self.logDirectory):
                os.makedirs (self.logDirectory)
            logFile = os.path.join (self.logDirectory, toFile)
            if os.path.exists (logFile):
                try:
                    os.remove (logFile)
                except OSError as e:
                    logging.error ("unable to remove %s", logFile)
            handler = logging.handlers.RotatingFileHandler (logFile,
                                                            maxBytes=10000000,
                                                            backupCount=3)
            self.fileHandler = handler

        root_logger = logging.getLogger ()
        root_logger.setLevel (level)
        formatter = logging.Formatter ("%(asctime)s - %(levelname)s - %(message)s")
        formatter = logging.Formatter ("%(levelname)s: %(message)s")
        handler.setFormatter (formatter)
        root_logger.addHandler (handler)

    def getFileHandler (self):
        return self.fileHandler

    def setLogLevel (self, level):
        oldLevel = None
        if level:
            logger = logging.getLogger ()
            oldLevel = self.loggingLevel
            self.loggingLevel = level
            logger.setLevel (self.logLevels [level])
            return oldLevel

    @staticmethod
    def getInstance (logLevel=None, logDir=None, toFile=None):
        if not logLevel:
            logLevel = "info"
        if not logDir:
            logDir = "logs"
        if LogManager.theInstance == None:
            LogManager.theInstance = LogManager (logLevel, logDir, toFile)
        return LogManager.theInstance
        
