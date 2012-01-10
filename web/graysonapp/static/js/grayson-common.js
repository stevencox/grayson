
/*
===============================
==    J A V A S C R I P T    ==
===============================
*/
String.prototype.startsWith = function (str){
    return this.slice(0, str.length) == str;
};

// Array Remove - By John Resig (MIT Licensed)
Array.prototype.remove = function(from, to) {
    var rest = this.slice((to || from) + 1 || this.length);
    this.length = from < 0 ? this.length + from : from;
    return this.push.apply(this, rest);
};
if (! console.debug) {
    console.debug = function(name, value){
	console.warn("DEBUG: " + name + "==" + value);
    }
};
