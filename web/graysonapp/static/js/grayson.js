// get https if this is prod
if (graysonConf.uriPrefix == '/grayson' && ! graysonConf.unitTest) {
//if (graysonConf.uriPrefix !== '/' && ! graysonConf.unitTest) {
    if (location.href.indexOf("https://") == -1 && location.href.indexOf ("http://") > -1) {
	location.href = location.href.replace("http://", "https://");
    }
}

var grayson = null;

/*
===============================
==    J Q U E R Y            ==
===============================
*/
$.fn.exists = function () { return $(this).length > 0; };

/*
=========================================
==      G R A Y S O N   G R A P H      ==
=========================================
*/
function GraysonGraph () {
    this.graph = [];
    this.nodeMap = {};
    this.labelMap = {};
    this.isRoot = false;
    this.variableMap = {};
}
GraysonGraph.prototype.setVariableMap = function (varMap) {
    this.variableMap = varMap;
};
GraysonGraph.prototype.mapNode = function (node) {
    var label = node.label.text;
    this.nodeMap [node.id] = node;
    this.labelMap [label] = node;
    this.graph.push (node);
    node.graph = this;
};
GraysonGraph.prototype.byName = function (name) {
    var result = this.labelMap [name];
    if (result == null || result == 'undefined') {
	var literalToNodeId = this.variableMap['literalToNodeId'];
	if (literalToNodeId && name in literalToNodeId) {
	    var id = this.variableMap['literalToNodeId'][name];
	    if (id) {
		
		var numpat = new RegExp ('^[0-9]*'); // delete numeric prefix (compiler internal...?)
		id = id.replace (numpat, '');
		
		result = this.nodeMap [id];
		
		if (result != null) {
		    result.graphText.attr ('text', name);
		}
	    }
	}
    }
    if (result == null) {
	grayson.log_debug ('unable to map ' + name + ' in: ');
	for (k in this.nodeMap) {
	    grayson.log_debug (' -- ' + k + ' => ' + this.nodeMap [k].label.text);
	}
    }
    return result;
};
GraysonGraph.prototype.setRootGraph = function (isRoot) {
    this.isRoot = isRoot;
};

/*
===============================
== G R A Y S O N   M O D E L ==
===============================
*/
function GraysonModel () {
    this.clear ();
};
GraysonModel.prototype.clear = function () {
    this.graphs = {};
};
GraysonModel.prototype.add = function (node) {
    var graphId = basename (node.workflow);
    graphId = grayson.prefix (graphId);

    grayson.log_debug ("grayson:data:add: graphId: " + graphId + " node: " + node.label.text);
    if (graphId in this.graphs) {
    } else {
	this.graphs [graphId] = new GraysonGraph ();
	grayson.log_debug ("grayson:_initialized: graphId: " + graphId);
    }
    var graph = this.graphs [graphId];
    this.graphs[graphId].mapNode (node);
    grayson.log_debug ("mapped node: " + node.label.text + " in " + graphId);
};
GraysonModel.prototype.byId = function (workflowId, id) {
    workflowId = basename (workflowId);
    workflowId = grayson.prefix (workflowId);
    var graph = this.graphs [workflowId];
    return graph ? graph.nodeMap [id] : null;
};
GraysonModel.prototype.byName = function (workflowId, nodeName) {
    workflowId = basename (workflowId);
    workflowId = grayson.prefix (workflowId);
    var graph = this.graphs [workflowId]
    return graph ? graph.byName (nodeName) : null; 
    //return (graph && nodeName in graph.labelMap) ? graph.labelMap [nodeName] : null;
};
GraysonModel.prototype.getGraphNodes = function (graphId) {
    graphId = grayson.prefix (basename (graphId));
    var graph = this.getGraph (graphId);
    return graph ? graph.graph : null;
};
GraysonModel.prototype.getGraph = function (graphId) {
    var graph = null;
    graphId = basename (graphId);
    graphId = grayson.prefix (graphId);
    if (graphId in this.graphs) {
	graph = this.graphs [graphId];
    }
    return graph;
};
GraysonModel.prototype.createNode = function (args) { //workflow, id, json, fill, geom, shape, annotations, label) {
    if (args && args.id && args.workflow && args.geometry && args.label) {
	this.add ({
	    id        : args.id,
	    graphNode : null,
	    graphText : null,
	    graph     : null,
	    workflow  : args.workflow,
	    instances : [],

	    logdir    : null,
	    logid     : null,
	    daglog    : null,

	    contexts  : {},
	    selectedInstance : null,
	    annot     : args.annotations,

	    geom      : args.geometry,
	    fill      : args.fill,
	    shape     : args.shape,
	    label     : {
		    geom  : args.label.geometry,
		    style : {
			"stroke"      : args.label.textColor, 
			"fill"        : args.label.textColor, 
			"font-size"   : parseInt (args.label.fontSize),
		        "font-weight" : args.label.fontStyle,
		        "text-anchor" : "start",
		        "opacity"     : 1
		    },
		    text  : args.label.text
	    },
	    scheduler : {
		id     : null,
		status : null 
	    }
	});
    }    
};


/*
===============================
==  G R A Y S O N  T A B S   ==
===============================
*/
function GraysonTabs () {
    this.elementId = "#tabs";
    this.tabId = 0;
}
GraysonTabs.prototype.initialize = function () {
    if ($(this.elementId).exists ())
	$(this.elementId).remove ();
    $("body").append ($( '<div id="tabs" class="workflowTabs"><ul id="tab-labels"></ul></div>' ));
    $(this.elementId).tabs ();
};
GraysonTabs.prototype.addTab = function (name) {
    var id = ++this.tabId;
    var tabDivId = "tabs-" + id;
    var labelId = "g" + id;
    var tabId = "#" + tabDivId;
    var $tabs = $(this.elementId).tabs ("add", tabId, name).tabs ({
	    add: function (event, ui) {
		$tabs.tabs('select', '#' + ui.panel.id);
	    }
	});
    $(tabId).css ("display", "block");
    $(tabId).attr ("graphname", name);
    $tabs.tabs ('select', id);
    return tabDivId;
};
GraysonTabs.prototype.addDrawTab = function (name) {
    var tabId = this.addTab (name);
    var drawdivId = [ "drawdiv", tabId ].join ('-');
    var drawdiv = $([ '<div id="', drawdivId, '" class="drawdiv"></div>' ].join (''));
    $('#' + tabId).append (drawdiv);
    return drawdivId;
};
GraysonTabs.prototype.selectTab = function (indexOrId) {
    $(this.elementId).tabs('select', indexOrId);
};
GraysonTabs.prototype.hide = function () {
    $(this.elementId).hide ();
};

/*
===============================
==  G R A Y S O N   A P I    ==
===============================
*/
function GraysonAPI (grayson) {
    this.grayson = grayson;
    this.progress = 0;
    this.flowContext = {
	workflowId : null,
	workdir    : null,
	runId      : null
    };
};
GraysonAPI.prototype.getStaticURI = function (uri) {    
    return graysonConf.staticDataURL + uri;
}
GraysonAPI.prototype.localizeURI = function (uri) {
    var result = uri;
    var prefix = graysonConf.uriPrefix;
    if ( ! uri.startsWith ('/') ) {
	result = prefix == '/' ? 
	    prefix + uri : 
	    prefix + '/' + uri;
    }
    return result;
};
GraysonAPI.prototype.setFlowContext = function (context) {
    this.flowContext = context;
};
GraysonAPI.prototype.getFlowContext = function () {
    return this.flowContext;
};
GraysonAPI.prototype.formJobOutputURL = function (pattern) {
    return this.formJobOutputURI (this.flowContext.workdir,
				  basename (this.flowContext.workflowId).replace (".dax", ""),
				  this.flowContext.runId,
				  pattern);
};
GraysonAPI.prototype.formFlowFileURL = function (path, addUser) {
    var addUserParam = '';
    if (addUser) {
	addUserParam = 'addUser=true&';
    }
    return [ "get_flow_file?", addUserParam, "path=", path ].join ('');
};

/* TODO: investigate deleting job output stuff now that pats are event driven. */
GraysonAPI.prototype.formJobResourceArgs = function (workdir, workflowid, runid, jobid) {
    var args = [ "?workdir="     , workdir,
		 "&workflowid="  , workflowid,
		 "&runid="       , runid ];
    if (jobid) {
	args.push ("&jobid="     , jobid);
    }
    return args.join ("");
};
GraysonAPI.prototype.formJobOutputURI = function (workdir, workflowid, runid, jobid) {
    return [ "get_job_output",
	     this.formJobResourceArgs (workdir, workflowid, runid, jobid) ].join ('');
};


GraysonAPI.prototype.deleteWorkflow = function (args) {
    this.getJSON ('delete_run/?workdir=' + args.workdir + '&workflowid=' + args.workflowId + '&runid=' + args.runId, args.success, args.error);		  
};
GraysonAPI.prototype.progressPlus = function () {
    this.progress++;
    if (this.progress > 0) {
	$("#ajax-loader").show ();
    }
};
GraysonAPI.prototype.progressMinus = function () {
    this.progress--;
    if (this.progress <= 0) {
	this.progress = 0;
	$("#ajax-loader").hide ();
    }
};
GraysonAPI.prototype.getJSON = function (url, success, error) {
    this.ajax (url,	       
	      function (text) {
		  if (text) {
		      var response = grayson.api.parseJSON (text);
		      if (response) {
			  success (response);
		      }
		  }
	      },
	      error);

};
GraysonAPI.prototype.getXML = function (url, success, error) {
    this.ajax (url, success, error, 'xml');
};
GraysonAPI.prototype.postJSON = function (url, data, success, error) {
    this.post (url,
	       data,
	       function (text) {
		   if (text) {
		       var response = grayson.api.parseJSON (text);
		       if (response) {
			   success (response);
		       }
		   }
	       },
	       error);
};
GraysonAPI.prototype.parseJSON = function (text) {
    var object = null;
    if (text) {
	try {
	    var response = $.parseJSON (text);
	    if (response) {
		if (response.status && response.status === 'login_required') {
		    grayson.view.showLogin ();
		} else {
		    object = response;
		}
	    }
	} catch (e) {
	    console.log ("JSON parse error: " + text + "\n--(error): " + e.message);
	}
    }
    return object;
};
GraysonAPI.prototype.post = function (url, data, success, error, mimeType, method) {
    this.ajax (url, success, error, mimeType, "POST", data);
};
GraysonAPI.prototype.get = function (url, success, error, mimeType, method) {
    this.ajax (url, success, error, mimeType);
};
GraysonAPI.prototype.ajax = function (url, success, error, mimeType, method, data) {
    this.progressPlus ();
    var api = this;

    if (typeof (mimeType) !== 'string') {
	mimeType = "text";
    }
    if (typeof (method) !== 'string') {
	method = "GET";
    }
    var args = {
	    type     : method,
	    url      : this.localizeURI (url), 
	    dataType : mimeType,
	    success: function (text) {
       	        if (typeof (text) === 'string' && text.indexOf ("login_required") > -1) {
		    grayson.view.showLogin ();
		} else {
		    success (text);
		}
	    },
	    error: function (jqXHR, textStatus, errorThrown) {
		if (error) {
		    error (textStatus, errorThrown);
		} else {
		    grayson.log_error ("error: " + textStatus + " error: " + errorThrown);
		}
	    },
	    complete : function (jqXHR, textStatus) {
		api.progressMinus ();
	    }
    };

    if (typeof (data) === 'object') {
	args ['data'] = data;
	if (!safeMethod (method) && sameOrigin (url)) {
	    data ['csrfmiddlewaretoken'] = getCookie ('csrftoken');
	}
    }

    this.ajaxStub (args);

};
GraysonAPI.prototype.ajaxStub = function (args) {
    $.ajax (args);
};

/*
===============================
==     K I C K S T A R T     ==
===============================
TODO: possibly move this server side.
*/
function GraysonKickstart (text) {
    this.valid = false;
    if (text && text.startsWith ("<?xml")) {
	xml = $.parseXML (text);
	this.invocation = $(xml).find ("invocation");
	this.resource = this.invocation.attr ("resource");
	this.hostname = this.invocation.attr ("hostname");
	this.start = this.invocation.attr ("start");
	this.duration = this.invocation.attr ("duration");
	this.user = this.invocation.attr ("user");
	this.job = this.invocation.attr ("transformation");
	this.exitcode = $(xml).find ("regular").attr ('exitcode');
	this.stdout = $(xml).find ('statcall[id="stdout"]').find ("data").text ();
	this.stderr = $(xml).find ('statcall[id="stderr"]').find ("data").text ();
	this.valid = true;
    }
};

/*
=================================
== G R A Y S O N  E V E N T S  ==
=================================
*/
function GraysonEvents () {
    this.callbacks = {};
    this.lastEventTime = -1;
};
GraysonEvents.prototype.registerSet = function (handlers) {
	if (handlers) {
	    for (var c = 0; c < handlers.length; c++) {
		var handler = handlers [c];
		if (handler) {
		    this.register (handler.key, handler.callback);
		}
	    }
	}
};
GraysonEvents.prototype.register = function (eventType, callback) {
    if (eventType) {
	if (eventType instanceof Array) {
	    for (var c = 0; c < eventType.length; c++) {
		this.register (eventType [c], callback);
	    }
	} else {
	    var callbacks = this.callbacks [eventType];
	    if (! callbacks) {
		callbacks = [];
		this.callbacks [eventType] = callbacks;
	    }
	    callbacks.push (callback);
	}
    }
};
GraysonEvents.prototype.handleEvent = function (event) {
    var eventType = event.type;
    var callbacks = this.callbacks [eventType]
    if (callbacks) {
	var callback = null;
	for (var c = 0; c < callbacks.length; c++) {
	    callback = callbacks [c];
	    if (callback) {
		try {
		    callback (event);
		    this.lastEventTime = new Date ().getTime ();
		} catch (e) {
		    grayson.log_error ("grayson:event:eventType [" + eventType + 
				    "] callback produced exception: [" + e.message + 
				    "] for event: " + event + ", callback: " + callback);
		    throw e;
		}
		
	    }
	}
    } else {
	grayson.log_debug ("grayson:event:no-handler: event: " + eventType);
    }
};
GraysonEvents.prototype.heartbeat = function (event) {
    grayson.log_info ("events handling heartbeat event");
    var delta = event.time - this.lastEventTime;
    if (delta > (1000 * 3) ) {

	grayson.log_info ("heartbeat delta trigger");
	grayson.api.progressMinus ();
	grayson.api.progressMinus ();
	grayson.api.progressMinus ();
    }
};

/*
=============================
== G R A Y S O N  V I E W  ==
=============================
*/
function GraysonView (grayson) {
    this.APP_AUTH = 'app';
    this.GRID_AUTH = 'grid';

    this.tabs = new GraysonTabs ();
    this.grayson = grayson;
    if (window.GraysonDetail)
	this.detailView = new GraysonDetail (this.grayson);
    this.selectedWorkflow = null;
    this.context = {};
    this.authType = this.APP_AUTH;
};
GraysonView.prototype.showLogin = function (authTypeIn) {
    
    var authType = authTypeIn;
    if (! authTypeIn) {
	authType = this.APP_AUTH;
    }
    if (authType == this.APP_AUTH) {
	$('#login_kind').html ('Application Login');
    } else {
	$('#login_kind').html ('MyProxy Grid Login');
    }
    grayson.log_info ("auth-type: " + authType);
    this.authType = authType;

    $("#login_button").unbind ();
    $("#login_button").click (this.login);
	
    $("#login_password").unbind ('keyup');
    $("#login_password").keyup (function (event) {
	    if (event.keyCode == '13') {
		grayson.view.login ();
	    }
	});

    $('#loginDialog').dialog ('open');
};
GraysonView.prototype.setContext = function (workflowNodeName, instance) {
    this.context [workflowNodeName] = instance;
};
GraysonView.prototype.getContext = function () {
    return this.context [this.selectedWorkflow];
};
GraysonView.prototype.initialize = function () {
    var appView = this;
    if (this.detailView)
	this.detailView.initialize ();
    if (this.grayson.hasClientId ()) {
	$('#login_menu').html ("Logout");
    }
    $('#workflowUploadForm').ajaxForm ({
	    beforeSubmit: function (a, f, o) {
		o.dataType = "json";
		var url = $("#workflowUploadForm").attr ("action");
		o.url = appView.grayson.api.localizeURI (url);
		appView.grayson.prepareCanvas ();
		subscribe ();
	    },
	    success: function (object) {
		if (object.status && object.status === 'login_required') {
		    appView.showLogin ();
		} else {
		    if (object.status == "ok") {
			grayson.log_debug ('ok status');
		    }
		}
		$("#workflowUpload").dialog ('close');		
	    }
	});

    $("#workflowUpload").dialog ({
	    autoOpen : false,
		width     : 500,
		height    : 300,
		draggable : false,
		resizable : false,
		modal     : true
		});

    $("#flowDialog").dialog ({
	    autoOpen : false,
		width     : 500,
		height    : 350,
		maxWidth  : 500,
		draggable : false,
		resizable : true,
		modal     : true
		});

    $("#loginDialog").dialog ({
	    autoOpen      : false,
		width     : 500,
		height    : 300,
		draggable : false,
		resizable : false,
		modal     : true,
		show      : { effect : "fade", duration : 900 },
		hide      : { effect : 'fade', duration : 900 },
		focus     : function (event, ui) {
		// executes but is then overriden by something in jquery. get rid of settimeout()
		// breaks keycode keyup detector on password field set elsewhere.
		setTimeout (function () {
			$("#login_username").focus ();
			$("#login_password").keyup (function (event) {
				if (event.keyCode == '13') {
				    appView.login ();
				}
			    });
		    }, 500);
	    }
	});
    $("#login_menu").click (function (e) {
	    if (appView.grayson.hasClientId ()) {
		appView.grayson.api.getJSON ("logout/", function (response) {
			appView.grayson.prepareCanvas ();
			appView.tabs.hide ();
			appView.showAbout ();
			appView.grayson.setClientId ('');
			$("#login_menu").html ("Login");
		    });
	    } else {
		appView.showLogin ();
	    }
	});
    $("#title").click (function (e) {
	    if ($("#about").is (":visible") && 
		$("#tabs").exists () &&
		$("#tab-labels").html() !== '') 
		{
		    $("#about").hide ('fade');
		    $("#tabs").show ('fade');
		} else {
		appView.showAbout ();
	    }
	});

    $("#run_menu").click (function (e) {
	    if (appView.grayson.hasClientId ()) {
		$("#workflowUpload").dialog ('option', 'position', [ 71, 35 ]); 
		$("#workflowUpload").dialog ('open'); 
	    } else {
		appView.showLogin ();
	    }
	});
	
    $("#connect_menu").click (function (e) {
	    if (appView.grayson.hasClientId ()) {
		appView.initializeFlows ();
	    } else {
		appView.showLogin ();
	    }
	});
	
    $("#detail_menu").click (function (e) {
	    if (appView.detailView)
		appView.detailView.toggle ();
	});
    $("#gridauth_menu").click (function (e) {
	    appView.showLogin (appView.GRID_AUTH);
	});
	
    $('#jobOutputDialog').dialog({ autoOpen: false, width: 600 });
	
    var menuSelector = $.browser.msie ? "#title" : "ul.nav li";
    $(menuSelector).hover (function (event) { //When trigger is clicked...  
	    //Following events are applied to the subnav itself (moving subnav up and down)  
	    $(this).parent().find ("ul.subnav").slideDown ().show ('fade'); //Drop down the subnav on click  
	    $(this).parent().hover (function() {  
		},
		function(){  
		    //When the mouse hovers out of the subnav, move it back up  
		    $(this).parent().find("ul.subnav").slideUp('slow');
		});
	    //Following events are applied to the trigger (Hover events for the trigger)
	}).hover (function() {  
		//On hover over, add class "subhover"  
		$(this).addClass ("subhover");
	    },
	    function(){  //On Hover Out  
		$(this).removeClass ("subhover"); //On hover out, remove class "subhover"  
	    });
};
GraysonView.prototype.showAbout = function () {
    if (grayson.view.detailView)
	grayson.view.detailView.hide ();
    $("#tabs").hide ('fade');
    $("#modelName").html ('');
    $("#about").show ('fade');		
};
GraysonView.prototype.createFlowSelector = function (workflow, node) {
    var selector = "#" + node.id + "_tip";
    if (node && ( ! $(selector).exists () ) ) {
	var text =
	['<div class="tooltip" id="', node.id, '_tip"> ',
	 '   <div class="instanceSelectorContainer"> ',
	 '      <div class="instanceSelectorLabel">Select an instance to steer:',
	 '         <div class="instanceSelectorItemName" id="', node.id, '_prev">',
	 '         </div>',
	 '      </div>',
	 '      <div class="instanceSelectors" id="', node.id, '_instances"></div>', 
	 '	</div>',
	 '</div>' ].join ("");
	$("body").append ( text );
	$(selector); //.resizable ( { alsoResize : ');
    }
};
GraysonView.prototype.showFlowSelector = function (node) {
    var dom = $("#" + node.id);
    var tip = $("#" + node.id + "_tip");
    if (node && node.instances.length > 0) {
	var show = new Date().getTime ();
	$("#" + node.id).tooltip ({
		tip      : '#' + node.id + '_tip',
		delay    : 60,
		position : 'top right',
		offset   : [ node.geom.x + event.target.offsetTop, node.geom.y + event.target.offsetLeft],
		effect   : 'fade'
	 });
	var css = {
	    top  : node.geom.y - ( tip.height () * 0.7 ), //- tip.height () + dom.parent().position ().top - 20,
	    left : node.geom.x - (tip.width () / 2)  + (node.geom.width / 2)
        };
	if (css.top !== 'NaN' && css.left !== 'NaN') {
	    tip.css (css);
	}
    }
};
GraysonView.prototype.createFlowSelectors = function (graph) {
    var graph = this.grayson.model.getGraphNodes (graph);
    if (graph) {
	var node = null;
	for (var c = 0; c < graph.length; c++) {
	    node = graph [c];
	    this.createFlowSelector (graph, node);
	}
    }
};
GraysonView.prototype.findFlowTab = function (graphName) {
    var result = $('[graphname="' + graphName + '.graphml"]');
    return result;
};
GraysonView.prototype.selectWorkflow = function (graphName) {
    var tab = this.findFlowTab (graphName);
    var id = tab.id;
    if (tab.length > -1) {
	tab = tab [0];
	if (tab) {
	    id = tab.id;
	}
    }
    if (id) {
	this.tabs.selectTab (tab.id);
	this.selectedWorkflow = graphName;
    }
};
GraysonView.prototype.addFlowInstance = function (node, instance) {

    if ($.inArray (instance, node.instances) > -1) {
	return;
    }

    node.instances.push (instance);

    var after = 0;
    var before = 0;

    // keep it sorted
    node.instances.sort (function (L, R) {
	    var L_id = parseInt (grayson.getInstanceId (L));
	    var R_id = parseInt (grayson.getInstanceId (R));
	    return L_id - R_id;
	});

    var containerSelector = "#" + node.id + "_instances";
    var instanceNumber = parseInt (this.grayson.getInstanceId (instance));
    var id = node.id + '_' + instanceNumber;
    var base = basename (instance);
    var text = [ '<div class="instanceSelector" id="', id, '" instanceNumber="', instanceNumber, '" ',
		 '     value="', base, '"',
		 '     nodeId="', node.id, '"', 
		 '     title="', base, '">',
		 '</div>' ].join ('');
    $(containerSelector).append ( $(text) );

    // order selectors per sorted array
    for (var c = 0; c < node.instances.length; c++) {
	curr = node.instances [c];
	var id = this.grayson.getInstanceId (curr);
	var dom = $('#' + node.id + '_' + id);
	if (dom) {
	    dom.remove ();
	    $(containerSelector).append (dom);
	}
    }
    var appView = this;
    $(containerSelector + " > .instanceSelector").click (this.clickSelector)
    .hover (function (e) {
		var length = 30;
		var name = basename ($(this).attr ("value"));
		name = name.substring (0, Math.min (length, name.length));
		$("#" + node.id + "_prev").html (basename ($(this).attr ("value")));
	    },
	    function (e) {
		$("#" + node.id + "_prev").html ('');
	    });
};
GraysonView.prototype.clickSelector = function (event) {
    var appView = grayson.view;
    var value = $(this).attr ("value");
    if ( $(this).hasClass ("selectedItem") ) {
	// show the dagman and jobstatus logs for this sub-workflow
	if (false) { // this is just a bad idea right now.
	    var jobName = basename (value);
	    var paths = appView.getPaths (value, jobName);
	    if (paths) {
		
		var context = appView.getContext ();
		if (context !== null) {
		    jobName = [ context.instance, '.*?', jobName ].join ('');
		}
		
		appView.showJobOutput (appView.grayson.api.getFlowContext().workflowId,
				       jobName,
				       '',
				       paths.daglog, 
				       paths.jobstate);
	    }
	}
    } else {
	// If not selected, make it the selected sub-workflow instance
	var node = grayson.model.byId (grayson.api.getFlowContext ().workflowId,
				       $(this).attr ('nodeId'));
	//appView.setContext (node.label.text, value);

	appView.selectedWorkflow = node.label.text;
	var context = appView.newContext (value);
	appView.setContext (node.label.text, context);


	$(".instanceSelector").removeClass ("selectedItem");
	$(this).addClass ("selectedItem");
    }
};
GraysonView.prototype.newContext = function (name) {
    return {
	instance : name,
	events   : [],
	logdirs  : {}
    };
};
GraysonView.prototype.isClickable = function (node) {
    var annotation = node.annot;
    return ( annotation.type === 'reference' || 
	     annotation.type === 'executable' || 
	     annotation.type === 'file' || 
	     annotation.type === 'job' || 
	     (annotation.type === 'map' && annotation.style === 'dynamic') );
};
GraysonView.prototype.clickNode = function (event) {
    var appView = grayson.view;
    var target = $(event.target);
    var node = grayson.model.byId (target.attr ('wf'), event.target.id);
    if (node) {
	var annotation = node.annot;
	if (annotation) {
	    if (annotation.type == 'workflow' || annotation.type == 'dax') {
		var flowName = node.label.text;
		appView.selectWorkflow (flowName);

		var daxContext = appView.getContext ();
		if (daxContext && daxContext.instance) {
		    
		    var flowContext = appView.grayson.api.getFlowContext ();
		    
		    var subFlow = daxContext.instance.split ('.') [0];
		    var graphModel = grayson.model.getGraph (subFlow);
		    if (graphModel && graphModel.graph) {
			$.each (graphModel.graph, function (key, node) {
			    grayson.applyNodeState (node, 'blank', null, true);
			});
		    }

		    var objFile = appView.grayson.api.formFlowFileURL ([ flowContext.workdir,
									 daxContext.instance.replace ('.dax', '.obj') ].join ('/'),
								       true);
		    grayson.log_debug ('loading obj file: ' + objFile);
		    appView.grayson.api.getJSON (objFile,
						 function (object) {
						     /*
						     grayson.log_info ("got object: " + object);
						     console.log ('==================================================');
						     */

						     console.log (object);
						     var graphId = grayson.prefix (daxContext.instance);
						     var graph = grayson.model.getGraph (graphId);
						     if (graph) {
							 graph.setVariableMap (object);


							 grayson.log_info ('--> getting flow events: workflowId: ' + flowContext.workflowId + 
									   ', runId: ' + flowContext.runId);
							 appView.grayson.api.getJSON ([ 'get_flow_events/?workdir=', flowContext.workdir,
											'&workflowid=',              flowContext.workflowId,
											'&runid=',                   flowContext.runId,
											'&dax=',                     daxContext.instance  ].join (''),
										      function (response) {
											  if (response && response.status == 'ok') {
											  } else {
											      grayson.log_error ('error status: ' + response);
											  }
										      });


						     }
						 },
						 function (err) {
						     grayson.log_error ('got error: ' + err);
						 });


		}
	    } else if (appView.isClickable (node)) {
		var workflowId = node.graph.isRoot ? '' : appView.getContext().instance;
		var paths = appView.getPaths (workflowId, node.label.text, node);
		appView.grayson.api.get (paths.joblog, function (text) {
			appView.showJobOutput (paths.workflowId,
					       node.label.text,
					       text,
					       paths.daglog, 
					       paths.jobstate);
		    });
	    }
	}
    }
};
GraysonView.prototype.getPaths = function (workflowId, nodeName, pathNode) {

    var result = null;

    var topLevel = false;

    if (workflowId == null || workflowId.length == 0) {
	workflowId = grayson.api.getFlowContext ().workflowId;
	topLevel = true;
    }
    var useEventDrivenPaths = true;
    // note, this will need to become more dynamic to handle rescue dags and multiple job executions.
    if (useEventDrivenPaths && pathNode && pathNode.logdir) {
	var flowName = grayson.prefix (basename(workflowId).replace ('.dax',''));
	var parts = basename (workflowId).split ('.');
	var dagPrefix = flowName;
	if (parts && parts.length == 3) {
	    dagPrefix = parts.slice (0, 2).join ('.');
	}
	result = {
	    workflowId : flowName,
	    joblog     : [ pathNode.logdir, '/', pathNode.logid, '.out.000' ].join (''), 
	    daglog     : [ pathNode.logdir, '/', dagPrefix, '-0.dag.dagman.out' ].join (''),
	    jobstate   : [ pathNode.logdir, '/jobstate.log' ].join ('')
	};

	if (pathNode.daglog) {
	    result ['daglog'] = [ pathNode.logdir, '/', pathNode.daglog ].join ('');
	}

    } else if (workflowId.indexOf ('.dax') > -1) {
	result = {
	    workflowId : basename (workflowId).replace (".dax", ""),
	    joblog     : nodeName + "_.*?.out.000",
	    daglog     : "dagman.out",
	    jobstate   : "jobstate.log"
	};
	var jobstatePrefix = topLevel ? '' : '.*?' + result.workflowId + '/.*?';
	result.jobstate = jobstatePrefix + result.jobstate;

	var separator = topLevel ? '' : '/';
	result.daglog = ".*?" + result.workflowId + separator + ".*?" + result.daglog;
    }

    result.joblog = this.grayson.api.formFlowFileURL (result.joblog);
    result.jobstate = this.grayson.api.formFlowFileURL (result.jobstate);
    result.daglog = this.grayson.api.formFlowFileURL (result.daglog);

    return result;
};
GraysonView.prototype.showJobOutput = function (workflowId, nodeName, text, dagOutputURL, jobStatusLogURL) {    
    // if ! workflowId need to select workflow.
    grayson.log_debug ("grayson:got job output for wf:" + workflowId + ", jobid:" + nodeName);
    var globalNewline = new RegExp("\n", 'g');
    var jobOutput = $("#jobOutputDialog");
    var html = [];
    jobOutput.html ("");
    jobOutput.dialog ('option', 'title', "Status for workflow: [" + basename(workflowId) + "], job: [" + nodeName + "]");
    var error = "";
    var output = "";

    var kickstart = new GraysonKickstart (text);
    if (kickstart.valid) {
	output = kickstart.stdout.replace (globalNewline, "<br/>");
	error = kickstart.stderr.replace (globalNewline, "<br/>");
    }
    // Build Tabs
    html.push ('  <div id="outputTabs" class="outputTabSet">',
	       '    <ul>');
    
    if (kickstart.valid) {
	html.push ('      <li><a href="#general">General</a></li>',
		   '      <li><a href="#output">Output</a></li>',
		   '      <li><a href="#error">Error</a></li>');
    }
    html.push ('      <li><a href="#DAG">Workflow Log</a></li>',
	       '      <li><a href="#jobStatusLog">Job Status Log</a></li>',
	       '    </ul>');
    
    if (kickstart.valid) {
	html.push ('    <div id="general" class="jobOutputTab">',
		   '      <table style="margins:0">',
		   '        <tr><td class="jobInfo">resource</td><td>', kickstart.resource, '</td></tr>',
		   '        <tr><td class="jobInfo">hostname</td><td>', kickstart.hostname, '</td></tr>',
		   '        <tr><td class="jobInfo">user</td><td>', kickstart.user, '</td></tr>',
		   '        <tr><td class="jobInfo">job</td><td>', kickstart.job, '</td></tr>',
		   '        <tr><td class="jobInfo">exitcode</td><td>', kickstart.exitcode, '</td></tr>',
		   '        <tr><td class="jobInfo">start</td><td>', kickstart.start, '</td></tr>',
		   '        <tr><td class="jobInfo">duration</td><td>', kickstart.duration, '</td></tr>',
		   '      </table>',
		   '    </div>',
		   '    <div id="output" class="jobOutputTab">',
		   output,
		   '    </div>',
		   '    <div id="error" class="jobOutputTab">',
		   error,
		   '    </div>');
    }

    html.push ('    <div id="DAG" class="jobOutputTab">',
	       '    </div>',
	       '    <div id="jobStatusLog" class="jobOutputTab">',
	       '    </div>',
	       '  </div>');

    jobOutput.html (html.join (""));
    $("#outputTabs").tabs ();


    // DAG output
    this.grayson.api.get (dagOutputURL,  function (text) {
	    $("#DAG").html (text.replace (globalNewline, "<br/>"));
	});
    
    // Job Status Log
    this.grayson.api.get (jobStatusLogURL,  function (text) {
	    $("#jobStatusLog").html (text.replace (globalNewline, "<br/>"));
	});

    // Display
    jobOutput.dialog ('open');
    var leftEdge = 600;
    jobOutput.dialog ('option', 'width', $("#tabs").width () - (leftEdge + 20) + 1);
    jobOutput.dialog ('option', 'height', $("#tabs").height () - 360);
    jobOutput.dialog ('option', 'position', [leftEdge, 41]);
};
GraysonView.prototype.doDeleteWorkflow = function (event, args, displayNode) {
    args ['success'] = function (response) {
	if (response && response.status == "ok") {
	    displayNode.remove ();
	} else {
	    grayson.log_error ("error status: " + response);
	}
    };
    args ['error'] = function () {
	alert ('an error occurred deleting workflow (' + workflowId);
    };
    this.grayson.api.deleteWorkflow (args);
    event.stopPropagation ();
};
GraysonView.prototype.deleteWorkflow = function (event) {
    // event handler for deleting a workflow
    var flow = $(event.target).parent ();
    var args = {
	workdir    : flow.attr ('flow'),
	workflowId : flow.attr ('flow') + '/' + flow.attr ("flowname").replace ("_dax", ".dax"),
	runId      : ""
    };
    grayson.view.doDeleteWorkflow (event, args, flow);
};
GraysonView.prototype.deleteWorkflowRun = function (event) {
    // event handler for deleting a workflow run
    var flowRun = $(event.target).parent ();
    var args = {
	workdir     : flowRun.attr ('flow'),
	workflowId  : flowRun.attr ('flow') + '/' + flowRun.parent().parent().attr ("flowname").replace ("_dax", ".dax"),
	runId       : flowRun.attr ('runid')
    };
    grayson.view.doDeleteWorkflow (event, args, flowRun);
};
GraysonView.prototype.connectFlow = function (event) {
    var appView = grayson.view;
    var flowDialog = $("#flowDialog");
    flowDialog.dialog ('close');
    var workdir = $(event.target).attr ('flow');
    var runId = $(event.target).attr ('runid');
    var workflowId = workdir + '/' + $(event.target).attr ("flowname").replace ("_dax", ".dax");
    var graph = workdir + "/" + basename (workflowId).replace (".dax", ".graphml");

    appView.grayson.prepareCanvas ();
    $(".tooltip").remove ();
    appView.grayson.api.setFlowContext ({
	workdir    : workdir,
	workflowId : workflowId,
	runId      : runId,
	graph      : null
    });
    var limit = "/" + grayson.getClientId () + "/";
    var subscribeId = workflowId;
    for (var index = subscribeId.indexOf (limit); index > -1; index = subscribeId.indexOf (limit)) {
	subscribeId = subscribeId.substring (index + limit.length);
    }
    subscribe (subscribeId);
    appView.onRenderWorkflow (workflowId, graph, null, function (g) {
	appView.onRootGraphRendered (workflowId, graph, g);

	var daxen = [ basename (workflowId) ];
	for (var c = 0; c < g.graph.length; c++) {
	    var n = g.graph [c];
	    if (n && n.annot != null && (n.annot.type === 'workflow' || 
					 n.annot.type === 'dax'      || 
					 n.annot.type === 'map'      )) 
	    {
		if (n.label && n.label.text) {
		    console.log (n.annot + " " + n.label.text); 
		    daxen.push (n.label.text);
		}
	    }
	}
	appView.grayson.api.getJSON ([ 'get_flow_events/?workdir=', workdir,
				       '&workflowid=',              workflowId, 
				       '&runid=',                   runId,
				       '&dax=',                     daxen.join (',') ].join (''),
				     function (response) {
					 if (response && response.status == "ok") {
					 } else {
					     grayson.log_error ("error status: " + response);
					 }
				     });
	});

    appView.selectWorkflow (basename (graph).replace (".graphml", ""));
    if (appView.detailView)
	appView.detailView.setEventBufferSize (100);
};
GraysonView.prototype.onRootGraphRendered = function (flowId, graphName, graph) {
    base = dirname (flowId);
    var index = base.indexOf ('.');
    if (index) {
	base = base.substring (0, index);
    }
    $("#modelName").html (base + " : " + basename (graphName));
    graph.setRootGraph (true);

}
GraysonView.prototype.initializeFlows = function (callback) {
    var appView = this;
    this.grayson.api.getJSON ("connect_flows", function (flows) {
	    var flowDialog = $("#flowDialog");
	    var flowElement = $("#flows");
	    flowElement.html ("");
	    var text = [];
	    for (var c = 0, len = flows.length; c < len; c++) {
		var flow = flows [c];

		var configurationName = basename (flow.flow);
		if (configurationName.indexOf (".") > -1) {
		    configurationName = configurationName.split (".")[0];
		}
		var workflowName = flow.id.replace (".", "_");
		var id = workflowName + "_" + configurationName;
		id = id.replace (/-/g, "_");
		text.push ('<div class="flow" ',
			   '     flow="', flow.flow, '" ',
			   '     flowName="', workflowName, '" ',
			   '       id="', id, '"> ',
			   '     <span class="deleteWorkflow ui-icon ui-icon-closethick" style="float:right;" title="Delete this workflow and all its runs.">Delete</span>',
			   '             ', flow.id, ' (<b>', configurationName, '</b>)') ;

		for (var g = 0, glen = flow.graphs.length; g < glen; g++) {
		    text.push ('  <div class="', id, '_graph" value="', flow.flow, "/", basename (flow.graphs [g]), '"></div>');
		}

		for (var d = 0, dlen = flow.daxen.length; d < dlen; d++) {
		    text.push ('  <div class="', id, '_dax" value="', flow.daxen [d], '"></div>');
		}

		text.push ('      <div id="', id, '_runs" class="connectRuns">');
		var run = null;
		for (var r = 0, rlen = flow.runs.length; r < rlen; r++) {
		    var stateClass = 'runPending';
		    run = flow.runs [r];
		    var state = -1;
		    if (run.indexOf (' ') > -1) {
			parts = run.split (' ');		    
			run = parts [0];
			state = parts [1];
			if (state == '0') {
			    stateClass += ' runStatusSuccess';
			} else if (state == '1') {
			    stateClass += ' runStatusFailure';
			}
		    }
		    text.push ('     <div class="', id, '_run connectFlowRun" ',
			       '          flow="', flow.flow, '" ',
			       '          runid="', basename (run), '" ',
			       '       flowname="', workflowName, '">',
			       '         ', run,
			       '         <span class="', stateClass, '"></span>',
			       '         <span class="deleteWorkflowRun ui-icon ui-icon-closethick" style="float:right;" title="Delete this run.">Delete</span> ',
			       '     </div>');
		}
		text.push ('     </div>',
			   '</div>');
	    }
	    flowElement.append ($(text.join ("")));
	    $(".flow").click (function (e) {
		    var id = "#" + $(this).attr ("id") + '_runs';
		    $(id).toggle ();
		});
	    $(".deleteWorkflow").click (appView.deleteWorkflow);
	    $(".deleteWorkflowRun").click (appView.deleteWorkflowRun);
	    $(".connectFlowRun").click (appView.connectFlow);
	    flowDialog.dialog ('option', 'position', [ 71, 35 ]);
	    flowDialog.dialog ('open');
	    if (callback) {
		callback ();
	    }
	});
};
GraysonView.prototype.createConnections = function (graph, paths, paper) {
    if (graph != null) {
	for (var n = 0; n < graph.length; n++) {
	    var node = graph [n];
	    var connections = [];
	    for (var c = 0; c < paths.length; c++) {
		var path = paths [c];
		var source = null;
		var target = null;
		if (path.source && path.target) {
		    if (path.source.id == node.id || path.target.id == node.id) {
			if (path.source.id == node.id) {
			    source = node;
			    target = path.target;
			} else if (path.target.id == node.id) {
			    source = node;
			    target = path.target;
			}
			if (source && target && (source != target)) {
			    var connection = paper.connection (source.graphNode,
							       target.graphNode,
							       null,
							       "#9a9|2");
			    //connection.line.toBack ().toBack ();
			    connection.line.toFront().toFront ();
			    connections = paper ["connections"];
			    connections.push (connection);
			}
		    }
		}
	    }
	}
    }
};
GraysonView.prototype.renderGraphNodes = function (workflow, paper) {
    var appView = this;
    var graph = this.grayson.model.getGraphNodes (workflow);
    if (graph) {
	var minX = 0;
	var minY = 0;
	for (var c = 0; c < graph.length; c++) {
	    var node = graph [c];
	    if (node.geom.x < minX)
		minX = node.geom.x;
	    if (node.geom.y < minY)
		minY = node.geom.y;
	}
	var marginX = 10;
	var marginY = 10;
	for (var c = 0; c < graph.length; c++) {
	    var node = graph [c];
	    node.geom.x = node.geom.x - minX + marginY;
	    node.geom.y = node.geom.y - minY + marginY;
	    nodeAttrs = {
		id             : node.id,
		fill           : node.fill,
		stroke         : "#366",
		//r              : "3px", // breaks explorer horribly.
		cursor         : "move",
		connections    : []
	    };
	    if (node.instances.length > 0)
		nodeAttrs["class"] = "overlay-class";

	    var rectangle = null;
	    var width = 0;
	    var height = 0;
	    if (node.shape == 'ellipse') {
		width = node.geom.width / 2;
		height = node.geom.height / 2;
		rectangle = paper.ellipse (node.geom.x + width, node.geom.y + height, width, height).attr (nodeAttrs).toFront (); //.draggable.enable ();
	    } else {
		grayson.log_debug ("node geom x: " + node.geom.x + 
				   "node geom y: " + node.geom.y + 
				   "node geom w: " + node.geom.width + 
				   "node geom h: " + node.geom.height);
		rectangle = paper.rect (node.geom.x, node.geom.y, node.geom.width, node.geom.height).attr (nodeAttrs).toFront (); //.draggable.enable ();
	    }
	    var textSize = 10;
	    // unfortunate: render the text box to get its dimensions to calculate centering.
	    var text = paper.text (0, 0, node.label.text).toFront ().attr (node.label.style);
	    textWidth = text.getBBox().width;
	    textHeight = text.getBBox().height;
	    var textX = node.geom.x + ( (node.geom.width / 2) - (textWidth / 2));
	    var textY = node.geom.y + ( (node.geom.height / 2) - (textHeight / 8));
	    text.remove ();
	    var text = paper.text (textX, textY, node.label.text).toFront ().attr (node.label.style);

	    var set = paper.set ();
	    //set.draggable.enable ();
	    set.push (rectangle, text);
	    node.graphNode = rectangle;
	    node.graphText = text;
	    rectangle.node.id = node.id;

	    $(rectangle.node).unbind ();

	    $(rectangle.node).hover (function (e) {
		    var node = appView.grayson.model.byId (workflow, this.id);
		    appView.showFlowSelector (node);
		});

	    $(rectangle.node).attr ('wf', workflow);
	    $(rectangle.node).click (this.clickNode);
	}
    }
};
GraysonView.prototype.onRenderWorkflow = function (workflow, graphName, graphURI, callback) {
    var appView = this;
    var drawdivId = this.tabs.addDrawTab (basename (graphName));
    grayson.log_debug ([ 'workflow: ', workflow, ' graphName: ', graphName, ' graphURI: ', graphURI ].join (''));
    $('#' + drawdivId).html ("");
    var paper = new Raphael (drawdivId, "100%", "100%");
    //paper.draggable.enable ();
    paper ["connections"] = [];

    var NS = $.browser.webkit ? "" : "y\\:";
    var jsonKey = 'd5'; // ouch

    if (! graphURI) {
	graphURI = "get_workflow?workflow=" + graphName;
    }
    
    this.grayson.api.getXML (graphURI, function (xml) {
	grayson.log_debug ('grayson:renderworkflow: getworkflow.success (' + graphName + ')');
	var nodeDataKey = $(xml).find ("key[attr.name='description'][for='node']").attr ('id');
	var edgeDataKey = $(xml).find ("key[attr.name='description'][for='edge']").attr ('id');
	$(xml).find ('key').each (function () {
	    var attrName = $(this).attr ('attr.name');
	    var isFor = $(this).attr ('for');
	    if (attrName == 'description') {
		var id = $(this).attr ('id');
		if (isFor == 'node') {
		    nodeDataKey = id;
		} else if (isFor == 'edge') {
		    edgeDataKey = id;
		}
	    }
	});
	$(xml).find ('node').each (function (){
	    var id = $(this).attr ('id');
	    var folderType = $(this).attr('yfiles.foldertype');
	    if (! folderType) {
		var json = $(this).find (jsonKey).text ();
		var fill = $(this).find (NS + 'Fill').attr ('color');
		var geom = $(this).find (NS + 'Geometry');
		var shape = $(this).find (NS + 'Shape');
		var nodeDataExpr = "data[key='" + nodeDataKey + "']";
		var nodeDataExpr = "data";
		var annotations = null;
		$(this).find (nodeDataExpr).each (function () {
		    var text = $(this).text ();
		    var key = $(this).attr ('key');
		    if ( $(this).attr ('key') == nodeDataKey)
			annotations = $.parseJSON (text);
		});
		var label = null;
		// skip empty labels
		$(this).find (NS + 'NodeLabel').each (function () {
		    if ( $(this).text () !== '' ) {
			label = $(this);
		    }
		});
		var args = {
		    id          : id,
		    workflow    : workflow,
		    annotations : annotations,
		    fill        : fill,
		    shape       : shape ? shape.attr ('type') : 'rectangle',
		    geometry    : new Geometry (geom.attr ('height'),
						geom.attr ('width'),
						geom.attr ('x'),
						geom.attr ('y')),
		    label       : {
			geometry : new Geometry (label.attr ('height'),
						 label.attr ('width'),
						 label.attr ('x'),
						 label.attr ('y')),
			textColor  : label.attr ('textColor'),
			fontSize   : label.attr ('fontSize'),
			fontStyle  : label.attr ('fontStyle'),
			text       : label.text ()
		    }
		};
		appView.grayson.model.createNode (args); //workflow, id, json, fill, geom, shape, annotations, label);
	    }
	});
	var paths = [];
	$(xml).find ('edge').each (function () {
	    var id = $(this).attr ('id');
	    var source = appView.grayson.model.byId (workflow, $(this).attr ('source'));
	    var target = appView.grayson.model.byId (workflow, $(this).attr ('target'));
	    var json = $(this).find (jsonKey).text ();
	    $(this).find (NS + 'Path').each (function () {
		var path = {
		    source : source,
		    target : target,
		    sx : toFloat ($(this).attr ('sx')),
		    sy : toFloat ($(this).attr ('sy')),
		    tx : toFloat ($(this).attr ('tx')),
		    ty : toFloat ($(this).attr ('ty')),
		    points : []
		};
		paths.push (path);
		$(this).find (NS + 'Point').each (function () {
		    var px = toFloat ($(this).attr ('x'))
		    var py = toFloat ($(this).attr ('y'));
		    path.points.push ({ x : px, y : py });
		    grayson.log_debug ('grayson:parse:point: (x:' + px + ', y:' + py + ')');
		});
	    });
	});
	var graph = grayson.model.getGraphNodes (workflow);
	appView.renderGraphNodes (workflow, paper);
	appView.createConnections (graph, paths, paper);
	appView.createFlowSelectors (workflow);
	appView.grayson.processSubworkflows (workflow);
	appView.grayson.setEventBufferSize (0); 
	if (callback) {
	    callback (appView.grayson.model.getGraph (workflow));
	}
    });
};
Grayson.prototype.setEventBufferSize = function (size) {
	this.eventBufferSize = size;
};
GraysonView.prototype.login = function () {
    var appView = grayson.view;
    var post = {
	username            : $("#login_username").val (),
	password            : $("#login_password").val ()
    };
    $("#login_username").val ('');
    $("#login_password").val ('');

    var loginURL = 'login/';
    console.log ('auth type: ' + appView.authType);
    var appAuth = appView.authType === appView.APP_AUTH;
    if (! appAuth) {
	loginURL = 'grid_authenticate/';
    }

    if (post.username && post.username.length > 0 &&
	post.password && post.password.length > 0) {
	grayson.api.postJSON (loginURL,
			      post,
			      function (response) {
				  grayson.log_info ("login response " + response);
				  if (response.status === 'ok') {
				      $('#loginDialog').dialog ('close');
				      $('#login_menu').html ("Logout");
				      if (appAuth) {
					  grayson.setClientId (post.username);
					  subscribe ();
				      }
				  }
			      });
    }
};
GraysonView.prototype.hideCompilationMessages = function (flowId, logPath) {
    $("#compilationMessages").hide ();
};
GraysonView.prototype.clearCompilationMessages = function (flowId, logPath) {
    $("#compilationMessagesText").html ('');
};
GraysonView.prototype.showCompilationMessages = function (flowId, logPath) {
    this.tabs.hide ();
    if (this.detailView)
	this.detailView.hide ();
    this.grayson.api.get ('get_compile_msgs?log=' + logPath, function (data) {	    
	    $("#compileModelName").html (flowId);
	    $("#compilationMessages").show ();
	    $("#compilationMessagesText").html (data);
	});
};

/*
===============================
==      G R A Y S O N        ==
===============================
*/
function Grayson (args) {
    this.api = new GraysonAPI ();
    this.events = new GraysonEvents ();
    this.view = new GraysonView (this);
    this.eventBufferSize = 0;
    this.clientId = ''; 
    if (args) {
	this.clientId = args.clientId;
	this.events.registerSet (args.handlers);
    }
    this.initialize ();
};
Grayson.prototype.initialize = function () {
    this.model = new GraysonModel ();
    this.subworkflowEvents = [];
};
Grayson.prototype.prepareCanvas = function () {
    this.initialize ();
    this.view.tabs.initialize ();
    if (this.view.detailView)
	this.view.detailView.initialize ();
    this.view.clearCompilationMessages ();
    this.view.hideCompilationMessages ();
    $("#about").hide ();
    $('#jobOutputDialog').dialog ('close');
    this.setEventBufferSize (1000);
};
Grayson.prototype.log_info = function (m) {
    if (window.console && console.log) {
	window.console.log (m);
    }
};
Grayson.prototype.log_debug = function (m) {
    if (window.console && console.log) {
	window.console.debug (m);
    }
};
Grayson.prototype.log_error = function (m) {
    if (window.console && console.log) {
	window.console.error (m);
    }
};
Grayson.prototype.getBaseId = function (name) {
    var value = null;
    if (name) {
	var parts = name.split (".");
	value = parts [0];
    }
    return value;
};
Grayson.prototype.getNormalizedNodeName = function (name) {
    if (name !== null && name.startsWith ("subdax_")) {
	name = name.split ("_")[1];
	name = this.getBaseId (name);
	var id = parts [1]
    } else if (name.indexOf ("_") > -1) {
	name = name.substring (0,
			       name.lastIndexOf ("_"));
    }
    return name;
};
Grayson.prototype.isSyntheticJob = function (jobName) {
    var result = false;
    if (jobName) {
	var prefixes = [ 'create_dir_',
			 'clean_up_',
			 'stage_in_',
			 'stage_out_',
			 'chmod_',
			 'register_',
			 'INTERNAL'
			 ];
	for (var c = 0; c < prefixes.length; c++) {
	    if (jobName.startsWith (prefixes [c])) {
		result = true;
		break;
	    }
	}
    }
    return result;
};
Grayson.prototype.getColorMap = function () {
    return {
	"blank"     : '#366',     // the empty state
	"pending"   : '#06f',    // blue
	"executing" : '#ff3',    // yellow
	"failed"    : '#f00',    // red
	"succeeded" : '#3f0',    // green
	"1"         : '#ff0',    // red
	"0"         : '#3f0'     // green
    };
};
Grayson.prototype.prefix = function (str, sep) {
    var result = str;
    var sep = sep ? sep : '.';
    var index = str.indexOf (sep);
    if (index > -1) {
	result = str.substring (0, index);
    }
    return result;
};
Grayson.prototype.grokEvent = function (event) {
    var result = null;
    var state = event.state;
    var jobName = null;
    var jobId = null;
    var instanceId = null;
    var name = event.job;
    if (name) {
	if (name !== null && name.startsWith ("subdax_")) {
	    var parts = name.split ("_");
	    name = parts [1];
	    jobId = parts [ parts.length - 1 ];
	    parts = name.split (".");
	    jobName = parts [0];
	    instanceId = parts [1];
	} else if (name.indexOf ("_") > -1) { // padcswan_n1
	    var index = name.lastIndexOf ("_");
	    jobName = name.substring (0, name.lastIndexOf ("_"));
	    jobId = name.substring (index + 1);
	} else {
	    jobName = name;
	}
	result = {
	    state      : state,
	    jobName    : jobName,
	    jobId      : jobId,
	    instanceId : instanceId
	};
    }
    return result;
};
Grayson.prototype.updateNodeLogs = function (event, node) {
    if (event && node) {
	node.logdir = event.logdir;
	node.logid = event.job;
	if (event.detail && event.detail.daglog) {
	    node.daglog = event.log.daglog;
	}
	if (event.log && event.log.daglog) {
	    node.daglog = event.log.daglog;
	}
    }
};
Grayson.prototype.onUpdateJobStatus = function (event) {
    var grokedEvent = this.grokEvent (event);
    if (grokedEvent) {
	var colorMap = this.getColorMap ();
	if (grokedEvent.jobName && grokedEvent.state in colorMap) {
	    // a transfer job containing one or more files. update status for each node.
	    if (grokedEvent.jobName.indexOf ('stage_') == 0) {
		var transfer = null;
		var jobName = null;
		for (var c = 0, len = event.transfer.length; c < len; c++) {
		    transfer = event.transfer [c];
		    jobName = basename (transfer.sourceFile);
		    grokedEvent.jobName = jobName;

		    var node = null;

		    var applied = false;
/*
		    var flowName = grayson.prefix (basename (event.flowId));
		    if (flowName != null) {
			node = this.model.byName (flowName, grokedEvent.jobName);
			if (node) {
			    applied = this.applyNodeState (node, grokedEvent.state, event);
			}
		    }
*/
		    if (! applied) {
			if (node == null) {
			    grayson.applyEvent (event, grokedEvent);
			}
		    }
		}
	    } else {
		var node = this.model.byName (event.flowId, grokedEvent.jobName);
		if (node) {
		    if (grokedEvent.instanceId == null) {
			this.applyNodeState (node, grokedEvent.state, event);
		    } else if (grokedEvent.jobId) {
			// a subworkflow of a node with multiple instances.
			var subflowId = [ dirname (event.flowId), '/', grokedEvent.jobName, '.', grokedEvent.instanceId, '.dax' ].join ('');
			this.addSubworkflow (subflowId, node);
			var instanceSelector = "#" + node.id + "_" + grokedEvent.instanceId;
			var instance = $(instanceSelector);
			var color = this.getColorMap () [grokedEvent.state];
			instance.css ({ "background-color" : color });
			this.view.showFlowSelector (node);
		    }
		} else if (! this.isSyntheticJob (grokedEvent.jobName)) {
		    // a sub-workflow. render it.
		    if (event.job.startsWith ('subdax')) {
			var subflowId = [ dirname (event.flowId), '/', grokedEvent.jobName, '.', grokedEvent.instanceId, '.dax' ].join ('');
			this.renderSubFlow (subflowId, grokedEvent.jobName);
		    }
		}
		grayson.applyEvent (event, grokedEvent);
	    }
	}
    }
};
Grayson.prototype.applyEvent = function (event, grokedEvent) {
    var applied = false;
    var context = grayson.view.getContext ();
    var logdir = event.logdir;
    var logBase = basename (logdir);

    // for subdaxen, flow name will be the last thing before the underbar.
    var parts = logBase.split ('_');

    // root dax - flowName is second to last directory name in path.
    if (parts && parts.length == 1) {
	parts = logdir.split ('/');
    }


    if (parts && parts.length > 1) {
        var flowName = parts [ parts.length - 2 ]; // in scan-flow_scan-flowgid1 , this is 'scan-flow' - the end name.
        var concreteName = parts [1].replace ("gid", ".") + ".dax";
        var daxRunPattern = new RegExp ('[0-9]+\.dax');
        // todo: consolidate possible name patterns
        var concreteName3 = parts [1].
            replace ("gid", ".").
            replace (new RegExp ('\.[0-9]{3}'), '') + ".dax";

        concreteName = concreteName.replace (daxRunPattern, "dax");
        var concreteName2 = parts [0] + ".dax";

/*
	if ((! context) ||
	    (context && context.instance)) {
*/
	if (flowName) {
            var node = this.model.byName (flowName, grokedEvent.jobName);
            if (node) {
		applied = this.applyNodeState (node, grokedEvent.state, event);
            }
	}
	
/*
            if (context.instance.endsWith (concreteName)  ||
		context.instance.endsWith (concreteName2) ||
		context.instance.endsWith (concreteName3))
            {
	    }
//        }
*/
    }
    return applied;
};

Grayson.prototype.applyNodeState = function (node, state, event, immediate) {
    var applied = false;
    if (node && node.graphNode) {

	this.updateNodeLogs (event, node);

       	var color = this.getColorMap () [state];
	var stroke = 2;
	var delay = immediate ? 0 : 1000;

	if (state == 'running' || state == 'pending') {
	    node.graphNode.animate ({
		    stroke         : '#000',
		    opacity        : 0.7,
		    'stroke-width' : stroke,
		    title          : 'job status: ' + state
		}, delay);
	    node.graphNode.animate ({
		    stroke         : color,
		    opacity        : 0.7,
		    'stroke-width' : stroke,
		    title          : 'job status: ' + state
		    }, delay);
	    applied = true;
	} else {
	    node.graphNode.animate ({
		    stroke         : '#000',
		    opacity        : 1,
		    'stroke-width' : stroke,
		    title          : 'job status: ' + state
		}, delay);
	    node.graphNode.animate ({
		    stroke         : color,
		    opacity        : 1,
		    'stroke-width' : stroke,
		    title          : 'job status: ' + state
	    }, delay);	    
	    applied = true;
	}
    }
    return applied;
};
/*
Grayson.prototype.applyEvents = function (events) {
    if (events) {
	var context = this.view.getContext ();
	if (context && context.instance) {
	    for (var c = 0; c < events.length; c++) {		
		var event = events [c];
		var grokedEvent = this.grokEvent (event);
		var logdir = event.logdir;
		var logBase = basename (logdir);
		var parts = logBase.split ('_');
		if (parts && parts.length > 1) {
		    var flowName = parts [ parts.length - 2 ]; // in scan-flow_scan-flowgid1 , this is 'scan-flow' - the end name.
		    var concreteName = parts [1].replace ("gid", ".") + ".dax";
		    var daxRunPattern = new RegExp ('[0-9]+\.dax');

		    // todo: consolidate possible name patterns
		    var concreteName3 = parts [1].
			replace ("gid", ".").
			replace (new RegExp ('\.[0-9]{3}'), '') + ".dax";

		    concreteName = concreteName.replace (daxRunPattern, "dax")
		    var concreteName2 = parts [0] + ".dax";
		    if (context.instance.endsWith (concreteName) ||
			context.instance.endsWith (concreteName2) ||
			context.instance.endsWith (concreteName3)) 
		    {
			if (flowName) {
			    var node = this.model.byName (flowName, grokedEvent.jobName);
			    if (node) {
				this.applyNodeState (node, grokedEvent.state, event);
			    }
			}
		    }
		}
	    }
	}
    }
};
*/
Grayson.prototype.processSubworkflows = function (workflow) {
    grayson.log_debug ("grayson:process-subworkflows: ");
    consumedEvents = [];
    for (var c = 0; c < this.subworkflowEvents.length; c++) {
	var event = this.subworkflowEvents [c];
	if (event) {
	    var node = this.model.byName (workflow, event.element);
	    if (node) {
		event ['processed'] = true;
		this.addSubworkflow (event.flowId, node);
	    }
	}
    }
    for (var c = 0; c < this.subworkflowEvents.length; c++) {
	if (this.subworkflowEvents [c]['processed']) {
	    this.subworkflowEvents.remove (c);
	    c--;
	}
    }
};
Grayson.prototype.addSubworkflow = function (flowId, node) {
    var element = node.label.text + ".dax";
    if ($.inArray (flowId, node.instances) == -1) {
	this.view.addFlowInstance (node, flowId);
	if (node.selectedInstance == null) {
	    node.selectedInstance = flowId;
	    var context = this.view.newContext (flowId);
	    this.view.setContext (node.label.text, context);
	}
	if (node.annot.type == 'workflow' || node.annot.type == 'dax') {
	    this.renderSubFlow (flowId, element);
	}
    }
};
Grayson.prototype.renderSubFlow = function (subflowId, subflowName) {
    var graphPath = dirname (subflowId) + "/" + subflowName.replace (".dax", "") + ".graphml";
    var graphName = basename (graphPath).replace (".graphml", "");
    if (this.view.findFlowTab (graphName).length == 0) {
	this.view.onRenderWorkflow (subflowId, graphPath);
    }
};
Grayson.prototype.getInstanceId = function (instance) {
    var result = null;
    if (instance) {
	var parts = instance.split (".");
	result = parts [ parts.length - 2 ];
    }
    return result;
};
Grayson.prototype.setClientId = function (id) {
    this.clientId = id;
};
Grayson.prototype.hasClientId = function (id) {
    return this.clientId && this.clientId.length > 0;
};
Grayson.prototype.getClientId = function () {
    return this.clientId;
};
function graysonInit () {
    var eventHandlers = 
	[ 
	 // dispatch composite events to the event management system
	 {
	     key      : "composite",
	     callback : function (event) {
		 var an_event = null;
		 for (var c = 0; c < event.events.length; c++) {
		     an_event = event.events [c];
		     //console.log (an_event);
		     grayson.events.handleEvent (an_event);
		 }
	     }
	 },
	 // initialize tabs and render a new workflow.
	 {
	     key      : "workflow.structure",
	     callback : function (event) {
		 grayson.api.setFlowContext ({
			 workdir    : event.workdir,
			 workflowId : event.flowId,
			 runId      : basename (event.workdir),
			 graph      : null
		     });
		 grayson.view.tabs.initialize ();
		 grayson.view.onRenderWorkflow (event.flowId, event.graph, null, function (graph) {
			 grayson.view.onRootGraphRendered (event.flowId, event.graph, graph);
		     });
		 grayson.view.selectWorkflow (event.graph);
	     }
	 }, 
	 // annotate the graph with sub-workflow structure data
	 {
	     key      : "subworkflow.structure",
	     callback : function (event) {
		 grayson.subworkflowEvents.push (event);
		 if (grayson.eventBufferSize == 0) {
		     grayson.processSubworkflows ();
		 }
	     }
	 },
	 // update job status
	 {
	     key      : "jobstatus",
	     callback : function (event) {
		 grayson.onUpdateJobStatus (event);
	     }
	 },
	 {
	     key      : [ 'workflow.structure', 'subworkflow.structure', 'endEventStream', 'jobstatus' ],
	     callback : function (event) {
		 if (grayson.view.detailView)
		     grayson.view.detailView.addEvent (event);
	     }
	 },
	 {
	     key      : 'heartbeat',
	     callback : function (event) {
		 grayson.events.heartbeat (event);
	     }
	 },
	 {
	     key      : 'compilation-messages',
	     callback : function (event) {
		 grayson.view.showCompilationMessages (event.flowId, event.log);
	     }
	 }
	  ];

    var app = new Grayson ({
	    clientId : graysonConf.clientId,
	    handlers : eventHandlers
	});

    app.view.initialize ();

    return app;
}

/*
===============================
==           U T I L         ==
===============================
*/
function isNumber (n) {
    return (typeof (n) == "number");
};

function Geometry (height, width, x, y) {
    this.height = toFloat (height);
    this.width = toFloat (width);
    this.x = toFloat (x);
    this.y = toFloat (y);
};

function toFloat (x) {
    var result = x;
    if (! isNumber (x))
	result = parseFloat (x);
    return (result);
};

function dirname(path) {
    return path.replace(/\\/g,'/').replace(/\/[^\/]*$/, '');;
};

function basename(path) {
    return path ? path.replace(/\\/g,'/').replace( /.*\//, '' ) : '';
};

function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie != '') {
	var cookies = document.cookie.split(';');
	for (var i = 0; i < cookies.length; i++) {
	    var cookie = jQuery.trim(cookies[i]);
	    // Does this cookie string begin with the name we want?
	    if (cookie.substring(0, name.length + 1) == (name + '=')) {
		cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
		break;
	    }
	}
    }
    return cookieValue;
}
function sameOrigin(url) {
    // url could be relative or scheme relative or absolute
    var host = document.location.host; // host + port
    var protocol = document.location.protocol;
    var sr_origin = '//' + host;
    var origin = protocol + sr_origin;
    // Allow absolute or scheme relative URLs to same origin
    return (url == origin || url.slice(0, origin.length + 1) == origin + '/') ||
	(url == sr_origin || url.slice(0, sr_origin.length + 1) == sr_origin + '/') ||
	// or any other URL that isn't scheme relative or absolute i.e relative.
	!(/^(\/\/|http:|https:).*/.test(url));
}
function safeMethod(method) {
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}


/*
 =================================================
 ==  Initialize the document. 
 ==  Execute things that need to happen only once.
 ==================================================
 */
$(document).ready(function() {

	grayson = graysonInit ();

	if (graysonConf.unitTest) {
	    grayson.unitTestSetup ();
	}
    });


/*
 =================================================
 == Unit Tests
 ================================================= */
Grayson.prototype.unitTestSetup = function () {
    grayson.log_info ("executing unit tests");
    var text = ['<div id="qunit" style="z-index:2;position:absolute;top:0;width:100%;height:100%;display:block;">',
		'   <h1 id="qunit-header">Grayson QUnit Test Suite</h1>',
		'   <h2 id="qunit-banner"></h2>',
		'   <div id="qunit-testrunner-toolbar"></div>',
		'   <h2 id="qunit-userAgent"></h2>',
		'   <ol id="qunit-tests"></ol>',
		'   <div id="qunit-fixture">test markup</div>',
		'</div>' ].join ('');
    $("body").append ( $ ( text ) ).css ({ overflow : 'auto' });
    $("#qunit").click (function () {
	    $(this).fadeToggle ();
	});
    $("#test_menu").click (function () {
	    $("#qunit").fadeToggle ();
	});
};

