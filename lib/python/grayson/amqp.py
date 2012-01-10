import pika

class PikaPublisher(object):


    def __init__(self, exchange_name):
        self.exchange_name = exchange_name
        self.queue_exists = False

    def publish(self, message, routing_key):
        conn = pika.AsyncoreConnection(pika.ConnectionParameters(
                '127.0.0.1',
                credentials=pika.PlainCredentials('guest', 'guest')))

        ch = conn.channel()

        ch.exchange_declare(exchange=self.exchange_name, type="fanout", durable=False, auto_delete=False)

        ch.basic_publish(exchange=self.exchange_name,
                         routing_key=routing_key,
                         body=message,
                         properties=pika.BasicProperties(
                                content_type = "text/plain",
                                delivery_mode = 2, # persistent
                                ),
                         block_on_flow_control = True)
        ch.close()
        conn.close()
    
    def monitor(self, qname, callback):
        conn = pika.AsyncoreConnection(pika.ConnectionParameters(
                '127.0.0.1',
                credentials=pika.PlainCredentials('guest', 'guest')))

        ch = conn.channel()

        if not self.queue_exists:
            ch.queue_declare(queue=qname, durable=False, exclusive=False, auto_delete=False)
            ch.queue_bind(queue=qname, exchange=self.exchange_name)
            print "Binding queue %s to exchange %s" % (qname, self.exchange_name)
            #ch.queue_bind(queue=qname, exchange=self.exchange_name, routing_key=qname)
            self.queue_exists = True

        ch.basic_consume(callback, queue=qname)

        pika.asyncore_loop()
        print 'Close reason:', conn.connection_close

class GraysonAMQP:
    def __init__(self):
        self.publisher = publisher = PikaPublisher ()
        publisher.monitor ("q-x", greet)
    def send (self, message):
        self.publisher.publish ("hi", "q-x")

__all__ = [ "GraysonAMQP" ]
'''
def greet ():
    print "========================================== hi"

if __name__ == "__main__":
'''

#    main (sys.argv[1:])









