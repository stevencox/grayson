
Object.size = function(obj) {
    var size = 0, key;
    for (key in obj) {
        if (obj.hasOwnProperty(key)) size++;
    }
    return size;
};

function Gsn_A () {
};

Gsn_A.prototype.on = function (evt) {
    console.log ('on(' + evt + ')');
    if (evt === 'flows') {
	var flows = $('.flowName');
	var flow = null;
	var text = null;
	for (var c = 0, len = flows.length; c < len; c++) {
	    flow = flows [c];
	    text = flow.html ();
	    text = text.split (' ');
	    flow.html (text [0]);
	}
    } else if (evt === 'runs') {
	var runs = $('.run');
	var run = null;
	var text = null;
	var status = null;
	for (var c = 0, len = runs.length; c < len; c++) {
	    run = $(runs[c]);
	    text = run.text ();
	    text = text.split (' ');
	    run.text (text [0]);
	   
	    if (text.length > 1) {
		if (text [1] === '0') {
		    status = 'runFail';
		    run.text (run.text () + ' (failed)');
		} else if (text [1] === '1') {
		    status = 'runGood';
		    run.text (run.text () + ' (finished)');
		}
	    }
	    run.addClass (status);
	}
	
    }
};

var gX = null;
$( document ).ready (function() {
	$('.ui-btn-back').live('tap',function() {
		history.back(); return false;
	    }).live('click',function() {
		    return false;
		});
	gX = new Gsn_A ();
    });
$( document ).delegate( "#main", "pageshow", function() {
	$('#back').hide ();
	$('#home').hide ();
    });
$( document ).delegate( "#flows", "pageshow", function() {
	$('#back').show ();
	$('#home').show ();
    });
$( document ).delegate( "#runs", "pagecreate", function() {
	$('#back').show ();
	$('#home').show ();
	gX.on ('runs');
    });
