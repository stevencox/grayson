# -*- coding: utf-8 -*-

''' system '''
from string import Template
import logging
import os
import traceback

import subprocess

logger = logging.getLogger (__name__)

# convert to use subprocess module. capture stderr.

class Executor:

    def __init__(self, context=None):
        self.context = context

    def execute (self, command, pipe=True, processor=None, raiseException=True):
        textCommand = command
        if self.context:
            template = Template (command)
            textCommand = template.substitute (self.context)
            logging.info ("   --context: %s" % self.context)

        logger.debug ("executing command: %s", textCommand)
        output = os.popen (textCommand)
        '''
        output = subprocess.Popen (textCommand, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
            '''
        line = output.readline ()
        while line:
            if processor:
                processor (line)
            else:
                logging.info ("           >:    %s", line.rstrip ())
            line = output.readline ()
        status = output.close ()
        if status and status != 0 and raiseException:
            logging.error ("error executing command: [%s]" % textCommand)
            raise ValueError ("error executing command: [%s]" % textCommand)


