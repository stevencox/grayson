var express = require ('express')
    , sys  = require ('sys')
    , amqp = require ('amqp')
    , url  = require ('url')
    , fs   = require ('fs')
    , io   = require ('socket.io')
    , sys  = require (process.binding('natives').util ? 'util' : 'sys')
    , server;

data = fs.readFileSync ('conf/grayson.conf', 'utf-8');
configuration = JSON.parse (data);
buffer = [];

var httpOpts = configuration.node.http;
if (httpOpts) {
    var optionKeys = [ 'key', 'cert', 'ca' ];
    for (index in optionKeys) {
	var key = optionKeys [index];
	log_debug ("configure-http-opts: detect option: " + key);
	if (key in httpOpts) {
	    var path = httpOpts [key];
	    log_debug ("configure-http-opts: option: " + key + " value: " + path);
	    if (path) {
		try {
		    httpOpts [key] = fs.readFileSync (path);
		    log_debug ("configure-http-opts: converted " + key + " to file contents.");
		} catch (e) {
		    log_error (e);
		    log_debug ("configure-http-opts: unable to read file: " + path);
		    process.exit (1);
		}
	    }
	}
    }
}

/** =============================================================== 
             S O C K E T . I O
    =============================================================== */
var server = httpOpts ? express.createServer (httpOpts) : express.createServer ()
    , io = io.listen(server)
    , sockets = { }
    , connections = new GraysonConnectionManager ()
    , messageID = 0
    , record = false;

io.set ('log level', configuration.node.logLevel); 

server.listen (configuration.socketioListenPort);

sys.puts ("Connected; listening on port: " + configuration.socketioListenPort);
sys.puts ("  - connected to AMQP message queue at port: " + configuration.amqpSettings.port);

var connection = amqp.createConnection (configuration.amqpSettings);

connection.addListener ('ready', function () {
	log_debug ("Connected to " + connection.serverProperties.product);
	var exchange = connection.exchange ("");
	var queue = connection.queue ('workflow', configuration.queueSettings);
	queue.bind (exchange, '#');
	queue.subscribe ("workflow", function (message) {
		try {
		    //log_debug (message.data);
		    var event = JSON.parse (message.data);
		    messageID++;
		    if (record) {
			fs.writeFile (messageID + ".evt", message.data, function (err) {
				if (err) {
				    sys.puts (err);
				} else {
				    sys.puts ("----------------The file was saved!");
				}
			    });
		    }

		    log_debug ("got message data: " + message.data + " broadcasting...");
		    connections.broadcast (event);
		} catch (e) {
		    log_error ("exception: " + e.message + "\nmessage: ");
		    printObj (message);
		}
	    });
	io.sockets.on ('connection', function (socket) {
		log_debug ('connection: ' + socket.sessionId);
		socket.on ('subscribe', function (message) {
			log_debug ("--message: " + message);
			var subscription = JSON.parse (message);
			if (subscription) {
			    var clientId = subscription.clientId;
			    printObj (subscription);
			    if (subscription.subscribe === "on") {
				log_debug ("client " + clientId + " registering for messages");
				connections.getConnection (clientId, socket).
				    setSubscription (subscription);
			    }
			}
		    });
		socket.on ('disconnect', function () {
			sys.puts (socket.sessionId + " disconnected...");
		    });
	    });
    });

connection.addListener('error', function(connectionException){
	if (connectionException.errno === process.ECONNREFUSED) {
	    sys.log ('ECONNREFUSED: connection refused to ' + connection.host + ':' + connection.port);
	} else {
	    sys.log (connectionException);
	}
    });


/* =================================================================
   == Connection Manager  
   ================================================================= */

function GraysonConnectionManager () {
    this.sockets = {};
    this.keys = [];
};
GraysonConnectionManager.prototype.getConnection = function (clientId, socket) {
    var result = null;
    if (clientId in this.sockets) {
	result = this.sockets [clientId];
	if (result) {
	    result.setSocket (socket);
	    log_debug ("configured socket for client " + clientId);
	}
    }
    if (! result) {
	log_debug ("added new socket: " + result);
	result = new GraysonConnection (clientId, socket)
	this.sockets [clientId] = result;
	this.keys.push (clientId);
	log_debug ("added new socket: " + result);
    }
    return result;
};
GraysonConnectionManager.prototype.broadcast = function (event) {
    log_debug ("broadcast - iterate sockets");
    for (var c = 0; c < this.keys.length; c++) {
	var key = this.keys [c];
	log_debug ("key : " + key);
	if (key in this.sockets) {
	    var socket = this.sockets [key];
	    if (socket instanceof GraysonConnection) {
		log_debug ("broadcast - socket: " + socket);
		socket.send (event);
	    }
	}
    }
};

/* =================================================================
   == Connection
   ================================================================= */

function GraysonConnection (socketId, socket) {
    this.socketId = socketId;
    this.socket = socket;
    this.buffer = [];
    this.subscription = {};
};
GraysonConnection.prototype.setSocket = function (socket) {
    this.socket = socket;
    this.flush ();
};
GraysonConnection.prototype.setSubscription = function (subscription) {
    this.subscription = subscription;
};
GraysonConnection.prototype.send = function (event) {
    if (this.socket) {
	this.emit (event);
    } else {
	this.buffer.push (event)
    }
};
GraysonConnection.prototype.flush = function () {
    var event = null;
    for (var c = 0; c < this.buffer.length; c++) {
	event = this.buffer [c];
	if (event) {
	    if (event.socketId === this.socketId) {
		//log_debug ("--(buffer-send): " + event);
		this.emit (event);
		this.buffer.remove (c);
	    }
	}
    }
};
GraysonConnection.prototype.emit = function (event) {
    var send = false;
    log_debug ("connection.send");
    if (this.subscription) {	
	if (this.subscription.flows) {
	    log_debug ("connection.send -- filter active.");    
	    filterActive = true;
	    var flow = null;
	    for (var c = 0; c < this.subscription.flows.length; c++) {
		flow = this.subscription.flows [c];
		log_debug ("connection.send -- filter flow: " + flow);
		if (event.flowId.match (flow)) {
		    send = true;
		    log_debug ("connection.send -- accept filtered flow: " + event.flowId);
		    break;
		} 
		if (! send) {
		    log_debug ("======================================================");
		    log_debug ("===== REJECTED MESSAGE : " + JSON.stringify (event));
		    log_debug ("======================================================");
		}
	    }
	} else {
	    send = true;
	}
    }
    if (send) {
	var data = JSON.stringify (event, null, 4);
	log_debug ("connection.emit -- sending: " + data);
	this.socket.emit ('message', JSON.stringify (event));
    }
};

/* =============================================================== 
   == Util
   =============================================================== */

function printObj (obj) {
    for (x in obj)
	sys.puts ("  '" + x + "':'" + obj [x] + "'");
}
function log_info (m) {
    sys.puts (new Date() + "INFO: " + m);
}
function log_debug (m) {
    sys.puts (new Date() + "DEBUG: " + m);
}
function log_error (m) {
    sys.puts (new Date() + "ERROR: " + m);
}
function contains(a, obj){
  for(var i = 0; i < a.length; i++) {
    if(a[i] === obj){
      return true;
    }
  }
  return false;
}
// Array Remove - By John Resig (MIT Licensed)
Array.prototype.remove = function(from, to) {
    var rest = this.slice((to || from) + 1 || this.length);
    this.length = from < 0 ? this.length + from : from;
    return this.push.apply(this, rest);
};

