
$.fn.dataTableExt.oApi.fnDisplayRow = function ( oSettings, nRow ) {
    var iPos = -1;
    for( var i=0, iLen=oSettings.aiDisplay.length ; i<iLen ; i++ ) {
	if( oSettings.aoData[ oSettings.aiDisplay[i] ].nTr == nRow ) {
	    iPos = i;
	    break;
	}
    }
    if( iPos >= 0 ) {
	oSettings._iDisplayStart = ( Math.floor(i / oSettings._iDisplayLength) ) * oSettings._iDisplayLength;
	this.oApi._fnCalculateEnd( oSettings );
    }
    this.oApi._fnDraw( oSettings );
}

function GraysonDetail (grayson) {
    this.grayson = grayson;
    this.eventCount = 0;
    this.eventBuffer = [];
    this.eventBufferSize = 5;
    this.monitorReady = false;
    this.eventId = 0;
    this.jobFailures = 0;
    this.netFailures = 0;
    this.protocolRe = new RegExp ("[a-zA-Z]+://");
    this.dirQ = null;

    this.eventTable = $("#eventTable").dataTable ({
	    bDestroy        : true,
	    bJQueryUI       : true,
	    sPaginationType : "full_numbers"
	}).css ({ width : "100%" });
    this.networkTable = $("#networkTable").dataTable ({
	    bDestroy        : true,
	    bJQueryUI       : true,
	    sPaginationType : "full_numbers"
	}).css ({ width : "100%" });

    //$('#monitor_text').resizable ();

    $("#detail_view").resizable ({
	    handles   : 'n',
	    maxHeight : 1000,
	    minHeight : 120
    });

    $("#detailTabs").tabs ({	    
	    show: function (event, ui) {
		if (ui.panel.id == 'compute_detail') {
    		    $("#compute_graph").html ("");
		    grayson.view.detailView.graphCompute ();
		}
	    }
	});
    var detailView = this;
    $('#detailTabs').bind ('tabsselect', function (event, ui) {
	    if (ui.panel.id == 'monitor_detail') {
		detailView.updateMonitor ();
	    } else if (ui.panel.id == 'file_detail') {
		detailView.updateFileTree ();
	    }
	});

    $("#compute_detail").resize (function () {
	    $("#compute_graph").html ("");
	    grayson.view.detailView.graphCompute ();
	});

    $(window).resize (function() {
	    var height = $("#detail_view").height ();
	    var top = $(window).height () - height;
	    $('#detail_view').css ({
		    position : "absolute",
		    bottom : "0px",
		    top    : top + "px",
		    height : height + "px",
		    width  : "100%"
	    });
	});

    var detailView = this;

    $('#job_fail').click (function (e) {
	    detailView.eventTable.fnFilter ('failed');
	    $("#detailTabs").tabs ('select', "#event_detail");
	});
    $('#net_fail').click (function (e) {
	    detailView.networkTable.fnFilter ('failed');
	    $("#detailTabs").tabs ('select', "#network_detail");
	});


};
GraysonDetail.prototype.updateFileTree = function () {
    var dir = $('#file_detail').attr ('dir');
    if (dir) {
	var maxDirLen = 55;
	var txt = dir.length > maxDirLen ? dir.substring ((dir.length - maxDirLen), dir.length - 1) : dir;
	$('#file_tree_path').html (txt);
	if (dir) {
	    var treeConfiguration = {
		root: dir + '/',
		script: 'dirlist/',
		expandSpeed: 200,
		collapseSpeed: 200,
		afterexpand : function () {
		    grayson.view.detailView.popDirQ ();
		}
	    };
	    $('#file_tree').fileTree (treeConfiguration, this.getFileText);
	}
    }
};

GraysonDetail.prototype.openDir = function (dir) {
    var id = [ '#ft_', dir ].join ('');
    $(id).click ();
    console.log (id);
};
GraysonDetail.prototype.navToFile = function (path) {
    var parts = path.split ('/');
    this.dirQ = [];

    for (var c = parts.length - 1; c > -1; c--) {
	var item = parts [c];
	if (item === '.') {
	    continue;
	} else {
	    while (item.indexOf ('-') > -1 || item.indexOf ('.') > -1) {
		item = item.replace ('-', '_');
		item = item.replace ('.', '_');
	    }
	    this.dirQ.push (item);
	}
    }
    this.popDirQ ();
};
GraysonDetail.prototype.popDirQ = function () {
    if (this.dirQ && this.dirQ.length > 0) {
	this.openDir (this.dirQ.pop ());
    }
};
GraysonDetail.prototype.getFileText = function (file) {
    grayson.api.get (grayson.api.localizeURI ('getfile?file=' + file), function (text) {
	    $('#file_detail_file_name').html (basename (file));	    
	    $('#file_detail_pane').html (text);
	    grayson.view.detailView.popDirQ ();
	});
};
GraysonDetail.prototype.updateMonitor = function () {
    var dir = $('#monitor_detail').attr ('dir');
    if (dir) {
	grayson.api.get (grayson.api.localizeURI ('get_flow_status?path=' + dir), function (text) {
		//text = [ '<pre>', text, '</pre>' ].join ('');
		$('#monitor_text').html (text);
	    });
    }
};
GraysonDetail.prototype.toggle = function () {
    var height = Math.min ( $("#detail_view").height (), 500);
    var top = $(window).height () - height;
    $('#detail_view').css ({
	    position   : "absolute",
		bottom : "0px",
		top    : top + "px",
		width  : "100%"
		});
    $("#detail_view").fadeToggle ('slow');
    $("#eventTable").dataTable ({
	    bDestroy        : true,
		bJQueryUI       : true,
		sPaginationType : "full_numbers"
		}).css ({
			width : "100%"
			    });    
    $("#networkTable").dataTable ({
	    bDestroy        : true,
		bJQueryUI       : true,
		sPaginationType : "full_numbers"
		}).css ({
			width : "100%"
			    });
};
GraysonDetail.prototype.hide = function () {
    $(".detailpanel-btn-slide").removeClass ("detailpanel-active");
    $("#detail_view").hide ();
};
GraysonDetail.prototype.show = function () {
    $(".detailpanel-btn-slide").addClass ("detailpanel-active");
    $("#detail_view").hide ();
    this.toggle ();
};
GraysonDetail.prototype.initialize = function (e) {
    if (this.eventTable) {
	this.eventTable.fnClearTable ();
	this.networkTable.fnClearTable ();
    }
    $("#dax_detail").html ('');
    $("#dax_detail_handle").hide ();
    $("#submit_detail").html ('');
    $("#submit_detail_handle").hide ();
    $("#file_detail_handle").hide ();
    $("#monitor_detail_handle").hide ();
    $("#detailTabs").tabs ('select', "#event_detail");
    $("#monitor_text").html ('');
    this.monitorReady = false;

    $('#monitor_detail').attr ('dir', null);
    $('#file_detail').attr ('dir', null);
    $('#file_detail_pane').html ('');


    this.jobFailures = 0;
    this.netFailures = 0;
    $('#detail_stats').removeClass ('failBorder');
    $('#net_fail').html ('');
    $('#job_fail').html ('');
};
GraysonDetail.prototype.setEventBufferSize = function (size) {
    this.eventBufferSize = size;
};
GraysonDetail.prototype.processEvent = function (event, html, netHtml) {
    if (event) {
	if (event.transfer) {
	    this.processNetworkEvent (event, netHtml);
	} else {
	    this.processGenericEvent (event, html);
	}
    }
};
GraysonDetail.prototype.getDetailText = function (event) {
    var text = '';
    if (event.detail) {
	var detail = event.detail;
	if (detail.stderr != null && detail.stdout != null) {
	    text = [ "STDOUT:\n", detail.stdout, "\n-----------------------------------\nSTDERR:\n", detail.stderr ].join ('');
	}
    }
    return text;
};
GraysonDetail.prototype.processGenericEvent = function (event, html) {
    var type = event.type;
    var target = basename (event.flowId);
    var value = "";
    var status = "";
    var time = new Date ();
    var workdir = "";
    var logText = [ "<br/>",  type ];
    var detailText = "";
    var eventIds = [];
    var eventTxt
    if (type == "jobstatus") {
	target = event.job;
	value  = event.state;
	if (event.state == 'failed') {
	    value = this.getFailText ('job');
	}
	time.setTime (event.time * 1000);
	workdir = event.logdir;
	detailText = this.getDetailText (event);
	if (! this.monitorReady) {
	    if (event.logdir.match ('[0-9]{8}T[0-9]{6}\-[0-9]{4}$') != null) {

		var prefix = "/var/workflow";
		var prefixLoc = event.logdir.indexOf (prefix);
		if (prefixLoc > -1) {
		    event.logdir = event.logdir.substring (prefixLoc);
		}


		$('#monitor_detail').attr ('dir', event.logdir);
		$('#monitor_detail_handle').show ();
		$('#file_detail').attr ('dir', event.logdir);
		$('#file_detail_handle').show ();
		this.updateMonitor ();
		this.monitorReady = true;
	    }
	}

    }
    var dax = '';
    if (event.log && event.log.dax) {
	dax = event.log.dax;
    }
    eventIds.push (this.eventId++);
    html.push ( '<tr id="evt_' + this.eventId + '">',
		'   <td>', time, '</td>',
		'   <td>', type, '</td>',
		'   <td nowrap="true">',
		'      <div path="', workdir, '"',
		'           resource="', target, '"',
		'           dax="', dax, '">',
		target);
    if (target && target != 'INTERNAL') {
	html.push ('           <div class="linkToCondor"  >Condor</div>' );
    }
    if (target && !this.inSkipList (target)) {
	html.push ('         <div class="linkToDax"     >DAX</div>');
    }
    html.push ('      </div>',
	       '   </td>',
	       '   <td title="' + detailText + '">', value, '</td>',
	       '   <td>order: ', this.eventCount, '</td>',
	       '</tr>' );
    this.eventCount++;
};
GraysonDetail.prototype.inSkipList = function (target) {
    var result = false;
    var skip = [ 'clean_up', 
		 'subdax_',
		 'chmod',
		 'register_',
		 'create_dir_' ];
    for (var c = 0; c < skip.length; c++) {
	if (target.startsWith (skip [c])) {
	    result = true;
	    break;
	}
    }
    return result;
};
GraysonDetail.prototype.getFailText = function (type) {
    if (this.netFailures + this.jobFailures === 0) {
	$('#detail_stats').addClass ('failBorder');
    }
    if (type === 'net') {
	this.netFailures++;
    } else if (type === 'job') {
	this.jobFailures++;
    }
    $('#job_fail').html (this.jobFailures + ' Job Errors, ');
    $('#net_fail').html (this.netFailures + ' Transfer Errors');
    return '<font color="red">failed</font>';
};
GraysonDetail.prototype.processNetworkEvent = function (event, html) {
    if (event.transfer) {
	var transfer = null;
	var srcProtocol = null;
	var dstProtocol = null;
	var sourceSite = null;
	var destSite = null;
	var state = null;
	var time = new Date ();
	var detailText = null;
	for (var c = 0, len = event.transfer.length; c < len; c++) {
	    transfer = event.transfer [c];
	    detailText = this.getDetailText (event);
	    state = event.state;
	    time.setTime (event.time * 1000);
	    srcProtocol = this.protocolRe.exec (transfer.sourceFile);
	    srcProtocol = srcProtocol ? srcProtocol : 
	    dstProtocol = this.protocolRe.exec (transfer.destFile);
	    if (state == 'failed') {
		state = this.getFailText ('net');
	    }
	    html.push ( '<tr>',
			'   <td>', time, '</td>',
			'   <td title="', transfer.sourceFile, '">', basename(transfer.sourceFile), ' @ ', transfer.sourceSite.substring (1), '</td>',
			'   <td title="', transfer.destFile, '">', basename(transfer.destFile), ' @ ', transfer.destSite.substring (1), '</td>',
			'   <td>', srcProtocol, ' => ', dstProtocol, '</td>',
			'   <td title="', detailText, '">', state, '</td>',
			'   <td>', transfer.bytes, '</td>',
			'   <td>', transfer.time, '</td>',
			'   <td>', transfer.down, '</td>',
			'   <td>', transfer.up, '</td>',
			'</tr>' );
	}
    }
};
GraysonDetail.prototype.addEvent = function (event) {
    var type = event.type;
    var eventHtml = [];
    var netHtml = [];
    if (this.eventBufferSize > 0) {
	if (this.eventBuffer.length >= this.eventBufferSize || type == "endEventStream") {
	    var evt = null;
	    var tableData = [];
	    var event = null;
	    var fields = null;
	    for (var c = 0; c < this.eventBuffer.length; c++) {
		evt = this.eventBuffer [c];
		this.processEvent (evt, eventHtml, netHtml);
	    }
	    this.eventBuffer.length = 0;
	    this.appendEvents (eventHtml, netHtml);
	    if (type == "endEventStream") {
		grayson.api.progressMinus ();
		this.eventBufferSize = 0;
	    }
	} else {
	    this.eventBuffer.push (event);
	}
    } else {
	this.processEvent (event, eventHtml, netHtml);
	this.appendEvents (eventHtml, netHtml);
    }
};
GraysonDetail.prototype.appendEvents = function (eventHtml, netHtml) {
    $("#eventList").append ( $( eventHtml.join ('') ) );
    this.eventTable = $("#eventTable").dataTable ({
	    fnDrawCallback  : function () {
		grayson.view.detailView.addCondorLinks ();
		grayson.view.detailView.addDaxLinks ();
	    },
	    bDestroy        : true,
	    bJQueryUI       : true,
	    sPaginationType : "full_numbers"
	}).css ({ width : "100%" });
    this.showLastPage (this.eventTable);

    if (netHtml) {
	$("#networkEventList").html ( netHtml.join ('') );
	this.networkTable = $("#networkTable").dataTable ({
		bDestroy        : true,
		bJQueryUI       : true,
		sPaginationType : "full_numbers"
	    }).css ({ width : "100%" });
	this.showLastPage (this.networkTable);
    }
};
GraysonDetail.prototype.showLastPage = function (table) {
    var nodes = table.fnGetNodes ();
    if (nodes && nodes.length > 0) {
	var last = nodes [nodes.length - 1];
	table.fnDisplayRow (last);
    }    
};

/*
==================
==  C O N D O R ==
==================
*/
GraysonDetail.prototype.renderCondor = function (text) {
    var html = [ '<textarea id="submit_detail_text" rows="25" class="editorPane" >',
		 text,
		 '</textarea>',
		 '<button id="save_submit_detail">Save</button><p>(Not Implemented)</p>' ].join ("");
    $("#submit_detail").html (html);
    $("#submit_detail_handle").show ();
    $("#detailTabs").tabs ('select', "#submit_detail");
    $("#save_submit_detail").click (function (event) {
	    grayson.log_info ("saving " + $("#submit_detail_text").html ());
	});
};
GraysonDetail.prototype.onCondorLink = function (event) {
    var path = $(this).parent().attr ("path");
    var pattern = grayson.view.detailView.getPattern (path);
    grayson.api.get (grayson.api.formJobOutputURL (pattern + '/' + $(this).parent().attr ("resource") + ".sub"),
		     grayson.view.detailView.renderCondor);
};
GraysonDetail.prototype.addCondorLinks = function () {
    $(".linkToCondor").
    unbind ().
    click (this.onCondorLink);
};
/*
 ===========================
 == P E G A S U S ==
 ===================
*/
GraysonDetail.prototype.renderDax = function (text) {
    var html = [ '<textarea id="dax_detail_text" rows="35" class="editorPane" >',
		 text,
		 '</textarea>',
		 '<button id="save_dax_detail" >Save</button>' ].join ('');
    $("#dax_detail").html (html);
    $("#dax_detail_handle").show ();
    $("#detailTabs").tabs ('select', "#dax_detail");
    $("#save_dax_detail").click (function (event) {
	    grayson.log_info ("saving " + $("#dax_detail_text").html ());
	});
};
GraysonDetail.prototype.onDaxLink = function (event) {
    var path = $(this).parent().attr ("path");
    var runId = grayson.api.getFlowContext().runId;
    var parts = path.split ('/');
    var daxPath = [ parts [0], parts [1], parts [5] ].join ('/') + '.dax';
    var end = parts [parts.length - 1];
    if (end != runId) {
        var dax = $(this).parent().attr ('dax');
	daxPath = [ path, 'dax', dax ].join ('/');
    }
    grayson.api.get (grayson.api.formFlowFileURL (daxPath),
		     grayson.view.detailView.renderDax);
};
GraysonDetail.prototype.addDaxLinks = function () {
    $(".linkToDax").
    unbind ().
    click (this.onDaxLink);
};
GraysonDetail.prototype.getPattern = function (path) {
    var pattern = null;
    var runId = grayson.api.getFlowContext().runId;
    var index = path.indexOf (runId);
    if (index > -1) {
	pattern = path.substring (index + runId.length).substring (1);
    }
    return pattern;
};
GraysonDetail.prototype.graphCompute = function () {
    var r = Raphael("compute_graph"),
    pie = r.piechart(320, 240, 100, [55, 20, 13, 32, 5, 1, 2, 10], { legend: ["%%.%% - Enterprise Users", "IE Users"],
								     legendpos: "west",
								     href: ["javascript:grayson.view.detailView.go('http://raphaeljs.com')", 
									    /* "http://g.raphaeljs.com" */]});    
    r.text(320, 100, "Interactive Pie Chart").attr({ font: "20px sans-serif" });
    pie.hover(function () {
	    this.sector.stop();
	    this.sector.scale(1.1, 1.1, this.cx, this.cy);
	    
	    if (this.label) {
		this.label[0].stop();
		this.label[0].attr({ r: 7.5 });
		this.label[1].attr({ "font-weight": 800 });
	    }
	}, function () {
	    this.sector.animate({ transform: 's1 1 ' + this.cx + ' ' + this.cy }, 500, "bounce");
	    
	    if (this.label) {
		this.label[0].animate({ r: 5 }, 500, "bounce");
		this.label[1].attr({ "font-weight": 400 });
	    }
	});
};

GraysonDetail.prototype.go = function (u) {
    window.open (u);  
};
GraysonDetail.prototype.graphCompute0 = function () {

    // For horizontal bar charts, x an y values must will be "flipped"
    // from their vertical bar counterpart.
    var plot2 = $.jqplot('compute_graph', [
        [[2,1], [4,2], [6,3], [3,4]], 
        [[5,1], [1,2], [3,3], [4,4]], 
        [[4,1], [7,2], [1,3], [2,4]]], {
        seriesDefaults: {
            renderer:$.jqplot.BarRenderer,
            // Show point labels to the right ('e'ast) of each bar.
            // edgeTolerance of -15 allows labels flow outside the grid
            // up to 15 pixels.  If they flow out more than that, they 
            // will be hidden.
            pointLabels: { show: true, location: 'e', edgeTolerance: -15 },
            // Rotate the bar shadow as if bar is lit from top right.
            shadowAngle: 135,
            // Here's where we tell the chart it is oriented horizontally.
            rendererOptions: {
                barDirection: 'horizontal'
            }
        },
        axes: {
            yaxis: {
                renderer: $.jqplot.CategoryAxisRenderer
            }
        }
    });

};