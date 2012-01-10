var fs = require('fs');

/**
 * Wait until the test condition is true or a timeout occurs. Useful for waiting
 * on a server response or for a ui change (fadeIn, etc.) to occur.
 *
 * @param testFx javascript condition that evaluates to a boolean,
 * it can be passed in as a string (e.g.: "1 == 1" or "$('#bar').is(':visible')" or
 * as a callback function.
 * @param onReady what to do when testFx condition is fulfilled,
 * it can be passed in as a string (e.g.: "1 == 1" or "$('#bar').is(':visible')" or
 * as a callback function.
 * @param timeOutMillis the max amount of time to wait. If not specified, 3 sec is used.
 */
console.log ("defining waitFor");
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
                    phantom.exit(1);
                } else {
                    // Condition fulfilled (timeout and/or condition is 'true')
                    console.log("'waitFor()' finished in " + (new Date().getTime() - start) + "ms.");
                    typeof(onReady) === "string" ? eval(onReady) : onReady(); //< Do what it's supposed to do once the condition is fulfilled
                    clearInterval(interval); //< Stop this interval
                }
            }
        }, 100); //< repeat check every 250ms
};

console.log ("defining translate");
function translateFile (inputFile, outputFile, patterns) {
    try {
        input = fs.open (inputFile, "r");
        output = fs.open (outputFile, "w");
	
	var line = null;
	var done = false;
	for (var line = input.readLine (); line != null && !done; line = input.readLine ()) {
	    //console.log ("  in: " + line);
	    for (var c = 0; c < patterns.length; c++) {
		var pattern = new RegExp (patterns [c][0]);
		var replacement = patterns [c][1];
		line = line.replace (pattern, replacement);
		//console.log ("    --pattern: " + pattern + " => " + replacement);
	    }
	    //console.log (" out: " + line);
	    output.writeLine (line);
	    done = line.indexOf ("</html>") > -1;
	}
    } catch (e) {
        console.log (e);
    } finally {

	if (input) {
	    input.close ();
	}
	if (output) {
	    output.close ();
	}

    }
}

console.log ("testing args");
//if (phantom.args.length === 0 || phantom.args.length > 4) {
if (phantom.args.length > 4) {
    console.log('Usage: run-qunit.js URL');
    phantom.exit(1);
} else {
    console.log ("Running phantomjs tests...");
}

console.log ("creating web page");
var page = new WebPage();

// Route "console.log()" calls from within the Page context to the main Phantom context (i.e. current "this")
page.onConsoleMessage = function(msg) {
    console.log(msg);
};

var inputFile = 'web/pages/app.html';
var url = 'http://localhost:8000/static/app.html';
var staticURL = '/static/';
if (phantom.args.length === 3) {
    inputFile = phantom.args [0];
    url = phantom.args [1]; 
    staticURL = phantom.args [2];
}
/*
var inputFile = phantom.args [0];
var url = phantom.args [1]; 
var staticURL = phantom.args [2];
*/

var outputFile = "web/graysonapp/static/app.html"; //inputFile + ".out";
var patterns = [
		[ "{{ app.URL_PREFIX }}", "" ],
		[ "\{\{ app.title \}\}", "grayson" ],
		[ "\{%.*%\}", "" ],
		[ "\{\{ STATIC_URL \}\}", staticURL ], //"/static/" ],
		[ "location.href = ", "// location.href =" ]
		];

console.log ("translating " + inputFile + " to " + outputFile + " using " + patterns);
translateFile (inputFile, outputFile, patterns);

console.log ("opening page: " + url);
page.open(url, function(status){
    if (status !== "success") {
        console.log("Unable to access network");
	console.log ("status: " + status);
        phantom.exit(1);
    } else {
        waitFor(function(){
            return page.evaluate(function(){
                var el = document.getElementById('qunit-testresult');
                if (el && el.innerText.match('completed')) {
                    return true;
                }
                return false;
		});


	console.log ('-----rendering output image');
	page.render ("grayson-unit-test.png");

        }, function(){

            var failedNum = page.evaluate(function(){
                var el = document.getElementById('qunit-testresult');
                console.log(el.innerText);
                try {
                    return el.getElementsByClassName('failed')[0].innerHTML;
                } catch (e) { }
                return 10000;
            });

            var text = page.evaluate (function(){
                return document.getElementById('qunit').innerText;
            });
	    console.log ("=================================================================================================");
	    console.log (text);

	console.log ('rendering output image');
	page.render ("/var/www/html/build/grayson/grayson-unit-test.png");


            phantom.exit((parseInt(failedNum, 10) > 0) ? 1 : 0);
	},
	20001);

    }
});

