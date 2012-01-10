# -*- coding: utf-8 -*-

''' system '''
from string import Template
import logging
import os
import traceback

# convert to use subprocess module. capture stderr.

class Executor:

    def __init__(self, context=None):
        self.context = context

    def execute (self, command, pipe=True, processor=None):
        textCommand = command
        if self.context:
            template = Template (command)
            textCommand = template.substitute (self.context)
            logging.info ("   --context: %s" % self.context)
        output = os.popen (textCommand)
        line = output.readline ()
        while line:
            if processor:
                processor (line)
            else:
                logging.info ("           >:    %s", line.rstrip ())
            line = output.readline ()
        status = output.close ()
        if status and status != 0:
            logging.error ("error executing command: [%s]" % textCommand)
            raise ValueError ("error executing command: [%s]" % textCommand)


