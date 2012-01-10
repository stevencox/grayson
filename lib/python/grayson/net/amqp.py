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

#pika.log.setup(level=pika.log.INFO)

logger = logging.getLogger (__name__)

class GraysonAMQP(object):

    def __init__(self, port=None):
        self.queue = "default"
        self.port = port

    def connect (self, hostname="127.0.0.1"):
        self.channel = None
        if not self.port:
            self.port = 5672  # default
        hostname = socket.getfqdn ()
        logger.info ("grayson:amqp:connect host: %s, port: %s", hostname, self.port)
        self.connection = AsyncoreConnection(ConnectionParameters(host=hostname,
                                                                  port=self.port),
                                             self.on_connected)

    def setQueue (self, name):
        self.queue = name

    def setQueueDeclaredCallback (self, queueDeclaredCallback):
        self.queueDeclaredCallback = queueDeclaredCallback

    def ioloop (self):
        self.connect ()
        try:
            self.connection.ioloop.start()
        except KeyboardInterrupt:
            self.connection.close()
            self.connection.ioloop.start()

    def on_connected(self, connection):
        connection.channel(self.on_channel_open)

    def on_channel_open(self, channel_):
        self.channel = channel_
        logger.info ("grayson:amqp:open-channel:%s", self.queue)
        self.channel.queue_declare (queue=self.queue,
                                    passive=False,
                                    durable=False,
                                    exclusive=False,
                                    auto_delete=False,
                                    callback=self.on_queue_declared)

    def on_queue_declared(self, frame):
        try:
            logger.info ("grayson:amqp:queue-declared: %s", self.queue)
            self.queueDeclaredCallback (frame)
        except:
            trackeback.print_exc ()
        finally:
            pass
        #self.connection.close()

#http://www.rabbitmq.com/plugins.html#rabbitmq-management

class GraysonAMQPTransmitter (GraysonAMQP):

    def __init__(self, queue=None, hostname=None, port=None):
        super(GraysonAMQPTransmitter, self).__init__() 
        self.port = port
        self.setQueueDeclaredCallback (self.transmit)
        self.setQueue (queue)

    def send (self, buffer):
        self.buffer = buffer
        self.ioloop ()

    def transmit (self, frame):
        while len (self.buffer) > 0:
            message = self.buffer.pop (0)
            logger.info ("grayson:amqp:queue:%s %s", self.queue, message)
            self.channel.basic_publish (exchange='',
                                        routing_key=self.queue,
                                        body=message)
            #logging.info ("amqp: transmitting %s", message)
            self.connection.close()

class GraysonAMQPReceiver (GraysonAMQP):

    def __init__ (self, queue=None, hostname=None, port=None):
        super(GraysonAMQPReceiver, self).__init__() 
        self.port = port
        self.setQueueDeclaredCallback (self.do_receive)
        self.setQueue (queue)

    def receive (self, processor=None):
        self.processor = processor
        self.ioloop ()

    def do_receive (self, frame):
        self.channel.basic_consume (self.handle_delivery,
                                    queue=self.queue)

    def handle_delivery(self, channel, method_frame, header_frame, body):
        '''
        print "Basic.Deliver %s delivery-tag %i: %s" % (header_frame.content_type,
                                                        method_frame.delivery_tag,
                                                        body)
                                                        '''
        if self.processor:
            self.processor (body)
        self.channel.basic_ack(delivery_tag=method_frame.delivery_tag)
        self.connection.close()

__all__ = [ "GraysonAMQPReceiver", "GraysonAMQPTransmitter" ]
