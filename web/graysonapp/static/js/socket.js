
/*
===============================
==     S O C K E T . I O     ==
=============================== */

var socket = new io.connect (null, { port : graysonConf.socketioListenPort });

socket.on ('message', function (eventText) {
	if (eventText.substr(0, 3) == '~h~'){
	    grayson.log_info ("heartbeat event");
	    var heartbeat = {
		time : new Date ().getTime (),
		event : {
		    type : 'heartbeat'
		}
	    };
	    grayson.events.handleEvent (heartbeat);
	} else {
	    grayson.api.progressPlus ();
	    try {
		//grayson.log_debug (eventText);
		var message = $.parseJSON (eventText);
		grayson.log_debug (JSON.stringify (message, undefined, 3));
		grayson.events.handleEvent (message);
	    } catch (e) {
		grayson.log_error ('exception: ' + e.message);
	    }
	    grayson.api.progressMinus ();
	}
    });

function subscribe (flow) {
    if (grayson && grayson.hasClientId ()) {

	var subscription = {
	    clientId  : grayson.getClientId (),
	    subscribe : 'on'
	};

	if (flow) {
	    subscription ["flows"] = [ flow ];
	}
	var text = JSON.stringify (subscription);

	socket.emit ('subscribe', text);

    }
};
socket.on ('connect', function () {
	setConnectStatus ("Connected.");
	subscribe ();
	setTimeout ("setConnectStatus ('')", 3000);
    });
socket.on('disconnect', function() {
	setConnectStatus ("Disconnected.");
    });
socket.on('reconnect',  function() {
	setConnectStatus ("Reconnected");
    });
socket.on('reconnecting', function( nextRetry ){
	setConnectStatus ("Re-connect in " + nextRetry + "ms");
    });
socket.on('reconnect_failed', function(){
	setConnectStatus ("Reconnected failed.");
    });
function setConnectStatus (msg) {
    display = $("#status");
    if (msg == '') {
	display.hide ('slow');
    } else {
	display.show ('slow');
	display.html (msg);
    }
};
