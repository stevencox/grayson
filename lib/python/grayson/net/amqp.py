import sys
import time
import traceback
import logging

import pika
from os.path import exists, normpath
from pika.adapters import SelectConnection
from pika.adapters import AsyncoreConnection
from pika.connection import ConnectionParameters
from pika import BasicProperties
import pika.log
import socket

logger = logging.getLogger (__name__)

def pika_debug ():
    import pika.log
    pika.log.setup(pika.log.DEBUG, color=True)

class AMQPQueue (object):
    def __init__(self, name = "default", passive=False, durable=False, exclusive=False, auto_delete=False):
        self.name = name
        self.passive = passive
        self.durable = durable
        self.exclusive = exclusive
        self.auto_delete = auto_delete
    def __str__ (self):
        return "name=%s, passive=%s, durable=%s, exclusive=%s, auto_delete=%s" % (
            self.name,
            self.passive,
            self.durable,
            self.exclusive,
            self.auto_delete)    

class AMQPSettings (object):
    def __init__ (self, port=5672, hostname=None, vhost="/", queue=AMQPQueue ()):
        self.port = port
        self.hostname = hostname
        self.queue = queue
        self.vhost = vhost
    def __str__ (self):
        return "(port=%s, hostname=%s, queue=(%s), vhost=%s)" % (
            self.port,
            self.hostname,
            self.queue,
            self.vhost)

class GraysonAMQP (object):

    def __init__(self, amqpSettings):
        logger.debug ("amqpsettings: %s", amqpSettings)
        self.amqpSettings = amqpSettings

    def connect (self, hostname="127.0.0.1"):
        self.channel = None
        logger.info ("grayson:amqp:connect host: %s, port: %s",
                     self.amqpSettings.hostname,
                     self.amqpSettings.port)
        connectionParameters = ConnectionParameters (host         = self.amqpSettings.hostname,
                                                     virtual_host = self.amqpSettings.vhost,
                                                     port         = self.amqpSettings.port)
        self.connection = AsyncoreConnection (connectionParameters, self.on_connected)

    def setSettings (self, settings):
        self.amqpSettings = settings

    def setQueueDeclaredCallback (self, queueDeclaredCallback):
        self.queueDeclaredCallback = queueDeclaredCallback

    def ioloop (self):
        self.connect ()
        try:
            self.connection.ioloop.start ()
        except KeyboardInterrupt:
            self.connection.close ()
            self.connection.ioloop.start ()

    def on_connected (self, connection):
        connection.channel (self.on_channel_open)

    def on_channel_open (self, channel_):
        self.channel = channel_
        logger.info ("grayson:amqp:open-channel: (%s)", self.amqpSettings.queue.name)
        try:
            self.channel.queue_declare (queue       = self.amqpSettings.queue.name,
                                        passive     = False,
                                        durable     = False,
                                        exclusive   = False,
                                        auto_delete = False,
                                        callback    = self.on_queue_declared)
        except:
            traceback.print_exc ()

    def on_queue_declared (self, frame):
        try:
            logger.info ("grayson:amqp:queue-declared: %s", self.amqpSettings.queue)
            self.queueDeclaredCallback (frame)
        except:
            trackeback.print_exc ()
        finally:
            pass
        #self.connection.close()

#http://www.rabbitmq.com/plugins.html#rabbitmq-management

class GraysonAMQPTransmitter (GraysonAMQP):

    def __init__(self, amqpSettings):
        super (GraysonAMQPTransmitter, self).__init__(amqpSettings) 
        self.amqpSettings = amqpSettings
        self.setQueueDeclaredCallback (self.transmit)
        self.setSettings (self.amqpSettings)

    def send (self, buffer):
        self.buffer = buffer
        self.ioloop ()

    def transmit (self, frame):
        while len (self.buffer) > 0:
            message = self.buffer.pop (0)
            logger.info ("grayson:amqp:queue:%s %s", self.amqpSettings.queue, message)
            try:
                self.channel.basic_publish (exchange    = '',
                                            routing_key = self.amqpSettings.queue.name,
                                            body        = message)
            except:
                traceback.print_exc ()
        self.connection.close ()

class GraysonAMQPReceiver (GraysonAMQP):
    def __init__ (self, amqpSettings):
        super (GraysonAMQPReceiver, self).__init__() 
        self.amqpSettings = amqpSettings
        self.setQueueDeclaredCallback (self.do_receive)
        self.setSettings (self.amqpSettings)

    def receive (self, processor=None):
        self.processor = processor
        self.ioloop ()

    def do_receive (self, frame):
        self.channel.basic_consume (self.handle_delivery,
                                    queue = self.amqpSettings.queue.name)

    def handle_delivery(self, channel, method_frame, header_frame, body):
        if self.processor:
            self.processor (body)
        self.channel.basic_ack (delivery_tag = method_frame.delivery_tag)
        self.connection.close ()

__all__ = [ "GraysonAMQPReceiver", "GraysonAMQPTransmitter" ]
