


GraysonAPI.prototype.ajaxStub = function (args) {
	
    if (args.url.indexOf ("posttest") > -1) {

	equals (args.type, "POST");
	equal (args.data.post, 'data');
	args.success ("postresponse");

    } else if (args.url.indexOf ("gettest") > -1) {

	equals (args.type, "GET");
	args.success ("gettresponse");

    } else if (args.url.indexOf ("logintest") > -1) {
	equals ( $("#ajax-loader").is (":visible"), true);

	args.success ("login_required");

	equals ( $("#loginDialog").is (":visible"), true);
	$("#loginDialog").dialog ('close');

    } else if (args.url.indexOf ("errortest") > -1) {

	var jqXHR = null;
	args.error (jqXHR, "errorresponse");

    } else if (args.url.indexOf ("connect_flows") > -1) {
	
	args.url = graysonConf.staticDataURL + "js/test/connect_flows_response.txt";
	$.ajax (args);

	// workflow selector job output:
    } else if (args.url.indexOf ('get_job_output') > -1 && args.url.indexOf ('jobstate.log') > -1) {
	args.success ('delta-flow.18 jobstate log');
	graysonTest.on ('jobstate-url', args.url);
    } else if (args.url.indexOf ('get_job_output') > -1 && args.url.indexOf ('dagman.out') > -1) {
	args.success ('delta-flow.18 dagman.out');
	graysonTest.on ('daglog-url', args.url);



    } else {

	$.ajax (args);

    }
    

};

function GraysonTest () {
    this.events = {};
};
GraysonTest.prototype.register = function (event, func) {
    this.events [event] = func;
};
GraysonTest.prototype.on = function (event, data) {
    this.events [event] (data);
};
GraysonTest.prototype.getGraphURI = function (file) {
    return grayson.api.getStaticURI ('js/test/graphs/' + file);
};
GraysonTest.prototype.getEventURI = function (id) {
    return grayson.api.getStaticURI ('js/test/events/' + id + '.evt');
};
function waitFor(testFx, onReady, timeOutMillis) {
    var maxtimeOutMillis = timeOutMillis ? timeOutMillis : 3001, //< Default Max Timout is 3s
        start = new Date().getTime(),
        condition = false,
        interval = setInterval(function() {
            if ( (new Date().getTime() - start < maxtimeOutMillis) && !condition ) {
                // If not time-out yet and condition not yet fulfilled
                condition = (typeof(testFx) === "string" ? eval(testFx) : testFx()); //< defensive code
            } else {
                if(!condition) {
                    // If condition still not fulfilled (timeout but condition is 'false')
                    console.log("'waitFor()' timeout");
		    throw "Timeout after " + timeOutMillis + " milliseconds.";
                } else {
                    // Condition fulfilled (timeout and/or condition is 'true')
                    console.log("'waitFor()' finished in " + (new Date().getTime() - start) + "ms.");
                    typeof(onReady) === "string" ? eval(onReady) : onReady(); //< Do what it's supposed to do once the condition is fulfilled
                    clearInterval(interval); //< Stop this interval
                }
            }
        }, 100); //< repeat check every 250ms
};


graysonTest = new GraysonTest ();


/*
=============
== C O R E ==
=============
*/
module ("Grayson: JavaScript Core Extensions");

test ("String.startsWith()", function () {
	var startsWith = "this is a string".startsWith ("this is a");
	equals (startsWith, true);
    });

test ("Array.remove ()", function () {
	var array = [ 'a', 'b', 'c' ];
	array.remove (1);
	equals (array.length, 2);
	equals (array [array.length - 1], 'c');
    });

test ("JQuery.exists ()", function () {
	equals ( $("#title").exists (), true);
    });

/*
====================
== G R A Y S O N  ==
====================
*/
module ("Grayson: initialization");

test ("initialize Grayson", function () {
	grayson = graysonInit ();
    });

/*
==============
== V I E W  ==
==============
*/

module ("Grayson: View Structure");

test ("GraysonView.setConnectStatus()", function () {
	var value = "hello";
	setConnectStatus (value);
	equals ( $("#status").html (), value);
    });

test ("GraysonView.run_menu - Click", function () {
	$("#run_menu").bind ('click', function () {
		setTimeout (function () {
			equal ($("#workflowUpload").is (":visible"), true);
			$("#workflowUpload").dialog ('close');
		    }, 1000);
	    });
	$("#run_menu").click ();
    });

test ("GraysonView.connect_menu - Click", function () {
	grayson = graysonInit ();
	grayson.view.initializeFlows (function () {
		setTimeout (function () {
			equal ($("#flowDialog").is (":visible"), true);
			$("#flowDialog").dialog ('close');
		    }, 1000);
	    });
    });

test ("GraysonView.detail_menu - Click", function () {
	$("#detail_menu").bind ('click', function () {
		equal ($("#detail_view").is (":visible"), true);
		$("#detail_view").hide ();
	    });
	$("#detail_menu").click ();
    });

test ("GraysonView.onRenderWorkflow ", function () {
	expect (13);
	stop ();

	var graph = "lambda-uber.graphml";
	grayson.prepareCanvas ();
	grayson.view.onRenderWorkflow (graph,
				       graph,
				       graysonTest.getGraphURI (graph),
				       function () {
					   start ();
					   var svgTypes = { 
					       'rect' : '', 
					       'RECT' : '',
					       'ellipse' : '',
					       'ELLIPSE' : ''
					   };
					   for (var c = 0; c < 13; c++) {
					       equal ( $("#n" + c).get (0).tagName in svgTypes, true );
					   }
				       });


	graph = 'lambda-flow.graphml';
	grayson.view.onRenderWorkflow (graph, graph, graysonTest.getGraphURI (graph));

    });

/*
===============================
== G R A Y S O N   E V E N T ==
===============================
*/
module ("Grayson: Event Handling");
test ("grayson.events.handlEvent(): Empty Event: ", function () {
	expect (1);
	var event = {
	    event : {
		type : "test"
	    }
	};
	grayson.events.handleEvent (event);
	equals (true, true);
    });

test ("grayson.events.handleEvent(): Composite Event: ", function () {
	var events = 
	    [
	     {
		 workflowId : "",
		 event      : {
		     type   : "jobstatus",
		 }
	     }
	     ];
	var compositeEvent = {
	    workflowId : "",
	    event      : {
		events : events
	    }
	};    
	grayson.events.handleEvent (compositeEvent);
    });

test ("GraysonEvent.register", function () {

	// verify
	//    grayson composite event handler is registered and working
	//    all events in a composite event are delivered
	//    events are delivered in the order received
	
	expect (100);
	var counter = 0;

	// handle a test event by testing the value it contains
	var handler = {
	    key : "test",
	    callback : function (event) {
		equals (event.value, counter++);
	    }
	};
	
	// create a synthetic composite event 
	var events = [];
	for (var c = 0; c < 100; c++) {
	    events.push ({
		    type  : "test",
		    value : c
		});
	}
	var compositeEvent = {
	    type   : "composite",
	    events : events
	};

	// register the handler
	grayson.events.registerSet ( [ handler ] );

	// handle the events
	grayson.events.handleEvent (compositeEvent);
    });


test ("GraysonEvent.handleEvent: Composite events", function () {
	grayson.events.handleEvent (testEvent);
    });

test ("GraysonEvent.handlEvent: Recorded Events (Load a few thousand events. Verify instance selectors are shown and work.)", function () {


	return;

	grayson.prepareCanvas ();
	var graphs = [
		      'delta-uber.graphml',
		      'delta-flow.graphml'
		      ];
	for (var c = 0; c < graphs.length; c++) {
	    var graph = graphs [c];
	    var uri = graysonTest.getGraphURI (graph);
	    grayson.view.onRenderWorkflow (graph, graph, uri, function () {
		    grayson.view.selectWorkflow (graph.replace ('.graphml', ''));
		});
	}
	grayson.api.setFlowContext ({
		workdir    : "delta-test-context.grayson_upk/delta-uber.dax",
		workflowId : graphs [0].replace (".graphml", ""),
		runId      : "",
		graph      : graphs [0]
	});

	var setCount = 115;
	expect (2); //4);
	stop ();

	var score = 1;

	for (var e = 1; e <= setCount; e++) {
	    grayson.api.get (graysonTest.getEventURI (e),
			     function (text) {
				 var container = $.parseJSON (text);
				 if (container != null) {
				     var events = container.events;
				     if (events != null) {
					 for (var c = 0; c < events.length; c++) {
					     try {
						 var event = events [c];
						 event.flowId = event.flowId.replace ('.dax', '.graphml');
						 grayson.events.handleEvent (event);
					     } catch (e) {
						 console.log ('---ERROR: ' + e.message);
					     }
					 }
					 ++score;
					 if (score === setCount) {
					     var matches = 0;
					     var fired = false;

					     var statusMatches = false;
					     var daglogMatches = false;
					     var statusURLMatches = false;
					     var daglogURLMatches = false;

					     var check = function (url, jobstatusurl, daglogurl) {
						 if (! fired) {
						     if (!statusMatches)
							 statusMatches = $("#jobStatusLog").html () === "delta-flow.18 jobstate log";
						     if (!daglogMatches)
							 daglogMatches = $("#DAG").html () === "delta-flow.18 dagman.out";
						     if (!statusURLMatches)
							 statusURLMatches = url.indexOf (jobstatusurl) > -1;
						     if (!daglogURLMatches)
							 daglogURLMatches = url.indexOf (daglogurl) > -1;
						     
						     if (statusMatches && daglogMatches && statusURLMatches && daglogURLMatches && !fired) {
							 fired = true;
							 start ();
							 equals (true, true);
						     } else {
							 console.log (  "           url : " + url +
									"\n  jobstatusurl : " + jobstatusurl +
									"\n     daglogurl : " + daglogurl +
									"\n           url : " + url);
						     }
						 }
					     };
					     graysonTest.register ('jobstate-url', function (url) {
						     var expected = 'get_job_output?workdir=delta-test-context.grayson_upk/delta-uber.dax&workflowid=delta-uber&runid=&jobid=.*?delta-flow.18/.*?jobstate.log';
						     check (url, expected, null);
						 });
					     graysonTest.register ('daglog-url', function (url) {
						     var expected = 'get_job_output?workdir=delta-test-context.grayson_upk/delta-uber.dax&workflowid=delta-uber&runid=&jobid=.*?delta-flow.18/.*?dagman.out';
						     check (url, null, expected);
						 });

					     grayson.view.selectWorkflow (graphs [0].replace ('.graphml', ''));
					     $("#n10_18").click ();
					     $("#n10_18").click ();
					     equals ( $("#jobOutputDialog").is (":visible"), true);
					     $("#jobOutputDialog").dialog ('close');
					 }
				     }
				 }
			     },
			     function (error, text) {
				 console.log ("______: ERROR:  " + error + " " + text);
			     });
	}
    });

/*
================================
== G R A Y S O N   M O D E L  ==
================================
*/
module ("Grayson: Graph Model");
var nodeTest = {
    node1   : {
	workflow : 'graph0',
	id       : 'node0',
	label : {
	    text : "nodeName0"
	}
    },
    node2 : {
	workflow : 'graph1',
	id       : 'node1',
	label : {
	    text : "nodeName1"
	}
    },
    node3 : {
	workflow : 'graph1',
	id       : 'node3',
	label : {
	    text : "nodeName3"
	}
    }
};

test ("grayson.model.add", function () {
	grayson.model.add (nodeTest.node1);	
    });

test ("grayson.model.byId", function () {
	grayson.model.clear ();
	grayson.model.add (nodeTest.node1);
	var node = grayson.model.byId (nodeTest.node1.workflow,
				       nodeTest.node1.id);
	equals (node.id, nodeTest.node1.id);
    });

test ("grayson.model.byName", function () {
	grayson.model.clear ();
	grayson.model.add (nodeTest.node1);
	var node = grayson.model.byName (nodeTest.node1.workflow,
					 nodeTest.node1.label.text);
	notEqual (null, node);
	equal (node.label.text, nodeTest.node1.label.text);
    });

test ("grayson.model.getGraphNodes", function () {
	grayson.model.clear ();
	grayson.model.add (nodeTest.node1);
	grayson.model.add (nodeTest.node2);
	var graph = grayson.model.getGraphNodes (nodeTest.node1.workflow);
	equal (graph.length, 1);
	equal (graph [0].id, nodeTest.node1.id);	
    });

test ("grayson.model.getGraphNodes - Isolation", function () {
	grayson.model.clear ();
	grayson.model.add (nodeTest.node1);
	grayson.model.add (nodeTest.node2);
	grayson.model.add (nodeTest.node3);

	var graph = grayson.model.getGraphNodes (nodeTest.node2.workflow);
	equal (graph.length, 2);
	equal (graph [0].id, nodeTest.node2.id);
	equal (graph [1].id, nodeTest.node3.id);
    });

/*
==============
== T A B S  ==
==============
*/
module ("Grayson:Tabs");
test ("GraysonTabs.addTab()", function () {
	grayson = graysonInit ();
	grayson.view.tabs.initialize ();
	var id = "drawdiv";
	grayson.view.tabs.addDrawTab ("test");
	grayson.view.tabs.selectTab (id);
	var selected = $("#tabs").tabs ('option', 'selected');
	equal (selected, 0);

	var drawdiv = $("#drawdiv-tabs-1");
	equal (drawdiv.is (":visible"), true);

	equal (drawdiv.hasClass ("drawdiv"), true);

	var graphname = drawdiv.parent().attr ("graphname");
	notEqual (graphname, null);
    });



/*
============================
== G R A Y S O N   A P I  ==
============================
*/
module ("Grayson.API");

test ("Grayson.API.localizeURI", function () {
	var uri = grayson.api.localizeURI ("text");
	equal ( uri.startsWith (graysonConf.uriPrefix), true);
    });
test ("Grayson.API.[set/get]FlowContext", function () {
	var flowContext = {
	    workdir    : "abc",
	    workflowId : "def",
	    runId      : "ghi"
	};
	grayson.api.setFlowContext  (flowContext);
	var got = grayson.api.getFlowContext ();
	
	equal (got.workdir, flowContext.workdir);
	equal (got.workflowId, flowContext.workflowId);
	equal (got.runId, flowContext.runId);
    });

test ("Grayson.API.[set/get]FlowContext", function () {
	var flowContext = {
	    workdir    : "abc",
	    workflowId : "def",
	    runId      : "ghi"
	};
	grayson.api.setFlowContext  (flowContext);
	var uri = grayson.api.formJobOutputURL ("pattern");
	
	equal ( uri.startsWith ("get_job_output"), true);
	equal ( uri.indexOf ('pattern') > 0, true);
	equal ( uri.indexOf (flowContext.workdir) > 0, true);
	equal ( uri.indexOf (flowContext.workflowId) > 0, true);
	equal ( uri.indexOf (flowContext.runId) > 0, true);
    });

test ("Grayson.API.post ()", function () {
	var data = {
	    post : 'data'
	};
	grayson.api.post ("posttest", data, function (data) {
		equals (data, "postresponse");
	    });
    });

test ("Grayson.API.get ()", function () {
	grayson.api.get ("gettest", function (data) {
		equals (data, "gettresponse");
	    });
    });
test ("Grayson.API.ajax () - Login Test", function () {
	grayson.setClientId ('');
	grayson.api.ajax ("logintest", function (data) {
	    });
    });

test ("Grayson.API.ajax () - Error Test", function () {
	grayson.api.ajax ("errortest",
			  function () {},
			  function (text) {
			      equal (text, "errorresponse");
			  });
    }); 







var testEvent = {
    "flowId": "scan-test-context.grayson_upk/scan-uber.dax",
    "type": "composite",
    "events": [
{
    "transfer": {
	"down": "2.1 Kb/s)",
	"sourceFile": "file:///home/scox/dev/grayson/work/outputs/scox/pegasus/scan-uber/20111015T183717-0500/full-sifs.txt",
	"bytes": "1.0",
	"up": "268.9 B/s",
	"destFile": "file:///home/scox/dev/grayson/web/../var/workflows/scox/scan-test-context.grayson_upk/full-sifs.txt",
	"sourceSite": "#local",
	"time": "0",
	"destSite": "#local"
    },
    "state": "succeeded",
    "clientId": "scox",
    "detail": {
	"stderr": "",
	"stdout": "2011-10-15 19:42:06,069    INFO:  Reading URL pairs from stdin\n2011-10-15 19:42:06,069    INFO:  PATH=/none/bin:/home/scox/app/pegasus-3.0.2/bin:/usr/bin:/bin\n2011-10-15 19:42:06,070    INFO:  LD_LIBRARY_PATH=/none/lib:/home/scox/app/jdk1.6.0_21/jre/lib/amd64/server:/home/scox/app/jdk1.6.0_21/jre/lib/amd64:/home/scox/app/jdk1.6.0_21/jre/../lib/amd64:/home/scox/dev/grayson/stack/python/lib:\n2011-10-15 19:42:06,070    INFO:  Executing cp commands\n2011-10-15 19:42:06,073    INFO:  Stats: 1.0  transferred in 0 seconds. Rate: 268.9 B/s (2.1 Kb/s)\n2011-10-15 19:42:06,074    INFO:  NOTE: stats do not include third party gsiftp transfers\n2011-10-15 19:42:06,074    INFO:  All transfers completed successfully."
    },
    "flowId": "scan-test-context.grayson_upk/scan-uber.dax",
    "job": "stage_out_local_local_3_0",
    "logdir": "pegasus/scan-uber/20111015T183717-0500",
    "time": "1318722131",
    "type": "jobstatus"
},
{
    "state": "pending",
    "clientId": "scox",
    "flowId": "scan-test-context.grayson_upk/scan-uber.dax",
    "job": "register_local_3_0",
    "logdir": "pegasus/scan-uber/20111015T183717-0500",
    "time": "1318722141",
    "type": "jobstatus"
},
{
    "state": "pending",
    "clientId": "scox",
    "flowId": "scan-test-context.grayson_upk/scan-uber.dax",
    "job": "clean_up_stage_out_local_local_3_0",
    "logdir": "pegasus/scan-uber/20111015T183717-0500",
    "time": "1318722141",
    "type": "jobstatus"
},
{
    "state": "executing",
    "clientId": "scox",
    "flowId": "scan-test-context.grayson_upk/scan-uber.dax",
    "job": "register_local_3_0",
    "logdir": "pegasus/scan-uber/20111015T183717-0500",
    "time": "1318722141",
    "type": "jobstatus"
},
{
    "state": "pending",
    "clientId": "scox",
    "flowId": "scan-test-context.grayson_upk/scan-uber.dax",
    "job": "clean_up_reduce_1n3",
    "logdir": "pegasus/scan-uber/20111015T183717-0500",
    "time": "1318722141",
    "type": "jobstatus"
},
{
    "state": "succeeded",
    "clientId": "scox",
    "detail": {
	"stderr": "#Successfully worked on    : 1 lines.\n#Worked on total number of : 1 lines.",
	"stdout": ""
    },
    "flowId": "scan-test-context.grayson_upk/scan-uber.dax",
    "job": "register_local_3_0",
    "logdir": "pegasus/scan-uber/20111015T183717-0500",
    "time": "1318722146",
    "type": "jobstatus"
},
{
    "state": "executing",
    "clientId": "scox",
    "flowId": "scan-test-context.grayson_upk/scan-uber.dax",
    "job": "clean_up_reduce_1n3",
    "logdir": "pegasus/scan-uber/20111015T183717-0500",
    "time": "1318722151",
    "type": "jobstatus"
},
{
    "state": "executing",
    "clientId": "scox",
    "flowId": "scan-test-context.grayson_upk/scan-uber.dax",
    "job": "clean_up_stage_out_local_local_3_0",
    "logdir": "pegasus/scan-uber/20111015T183717-0500",
    "time": "1318722151",
    "type": "jobstatus"
},
{
    "state": "succeeded",
    "clientId": "scox",
    "detail": {
	"stderr": "",
	"stdout": ""
    },
    "flowId": "scan-test-context.grayson_upk/scan-uber.dax",
    "job": "clean_up_reduce_1n3",
    "logdir": "pegasus/scan-uber/20111015T183717-0500",
    "time": "1318722151",
    "type": "jobstatus"
},
{
    "state": "succeeded",
    "clientId": "scox",
    "detail": {
	"stderr": "",
	"stdout": ""
    },
    "flowId": "scan-test-context.grayson_upk/scan-uber.dax",
    "job": "clean_up_stage_out_local_local_3_0",
    "logdir": "pegasus/scan-uber/20111015T183717-0500",
    "time": "1318722151",
    "type": "jobstatus"
},
{
    "state": "succeeded",
    "clientId": "scox",
    "flowId": "scan-test-context.grayson_upk/scan-uber.dax",
    "job": "INTERNAL",
    "logdir": "pegasus/scan-uber/20111015T183717-0500",
    "time": "1318722156",
    "type": "jobstatus"
}
	       ],
    "clientId": "scox",
    "time": 1318863615.781824
};
