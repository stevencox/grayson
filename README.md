GRAYSON
=======

Grayson is a toolchain for designing, executing, debugging and sharing scientific workflows. It consists of
   1. An editor, yEd by yWorks, for creating visual workflow components
   2. A compiler for parsing and linking components into a workflow
   3. A visual debugger for executing and troubleshooting workflows

Editor: 
-------

yEd is a desktop application and GraphML editor. It provides point and click, drag and drop and other familiar user interface metaphors. Graph nodes may be annotated and all artifacts are saved as XML.

Compiler:
---------

The compiler is a python command line program which assembles GraphML models into an abstract syntax tree and emits a Pegasus DAX with all necessary catalogs.

It also proivides a packager which assembles workflow artifacts into a compressed archive for submission to the execution environment.

Execution Environment:
----------------------

The execution environment is a web application allowing upload and execution of packaged workflows.

It reads GraphML workflows with embedded JSON annotations and renders them using the HTML5 Canvas API.                                                                                     

It also compiles the workflow to a Pegasus WMS DAX and submits it for execution.

It provides monitoring infrastructure consisting of:
   - An AMQP message queue
   - A distributed task queue - Celery
   - Asynchronous event notification to the client via Node.js

This allows workflow events to be dynamically rendered on the user interface.

Installation
============

Prerequisites:
-------------

   1. Pegasus 3.0.1
   2. Condor 7.7.5+
   3. Globus
   4. Python 2.7

Overview:
---------

  Grayson is very much alpha. These are preliminary install instructions.

  These have been tested on Fedora and CentOS 5.7

    git clone git://github.com/stevencox/grayson.git
    export GRAYSON_HOME=$PWD/grayson
    source $GRAYSON_HOME/bin/setup.sh
    grayson-install --clean --frozen --python=$(which python2.7)

  This should leave you with these directories:

     grayson
       ├── bin
       ├── conf
       ├── event
       ├── lib
       ├── samples
       ├── target
       ├── var
       ├── venv
       └── web
     stack
       ├── apache
       ├── erlang
       ├── java
       ├── modwsgi
       ├── node
       ├── pegasus
       └── rabbitmq


Development Environment:
------------------------

To run in a development environment - 

    cd grayson
    export GRAYSON_HOME=$PWD
    source $GRAYSON_HOME/bin/setup.sh

    cp conf/dev.conf conf/grayson.conf  
    web/manage.py runserver 0.0.0.0:8000
    sudo bin/grayson-rabbit.sh
    web/manage.py celeryd -l debug
    node event/server.js

Production Instance:
--------------------
 
Install mod_wsgi in your apache instance and add this to the apache config:

    LoadModule wsgi_module modules/mod_wsgi.so
    WSGIDaemonProcess host.domain.name user=<user> group=<user> processes=2 threads=25
    WSGIProcessGroup host.domain.name
    WSGISocketPrefix run/wsgi
    WSGIScriptAlias /grayson /opt/grayson/current/web/apache/django.wsgi
    Alias /grayson/static/ <installdir>/web/graysonapp/static/
    <Directory <installdir>/web/graysonapp/static/>
       Order deny,allow
       Allow from all
    </Directory>
    LogLevel info

Copy <installdir>/bin/init.d/* to /etc/init.d and make sure they are executable.

You'll need to change paths in these to match your environment.

Copy <installdir>/prod.conf to <installdir>/grayson.conf
Edit <installdir>/grayson.conf to provide paths to web server certificates.

As root,

     <installdir>/start-rabbitmq
     /etc/init.d/grayson-httpd
     /etc/init.d/grayson-celeryd
     /etc/init.d/grayson-event

Modify firewall settings appropriately to allow access to both httpd and node. The default port for node is 8080 and can be set in <installdir>/grayson.conf.

Grayson is at https://<host.domain.name>/grayson


Next Steps
==========

Grayson is in early alpha. It has been tested with Pegasus 3.0.1.

Some things are clear:

   * Add support for, and move all samples to Pegasus 4.0.x
   * Move to using Pegasus STAMPEDE for event detection 
   * Use the SQLAlchemy STAMPEDE API provided by Pegasus
   * Modify event notification to scope events to the selected subworkflow - not the whole thing.
   * A non-graphical approach is needed at least as an option.


Build Environment
=================

Grayson's built at the [RENCI continuous integration system](http://continuousintegration.wordpress.com).

* [Automated Build](http://ci-dev.renci.org/hudson/view/RCI/job/rci-grayson/)
* [API Docs](http://ci-dev.renci.org/hudson/view/RCI/job/rci-grayson/javadoc/)
* [Coverage Report](http://ci-dev.renci.org/hudson/view/RCI/job/rci-grayson/507/cobertura/)
* [Static Analysis](https://ci-dev.renci.org/hudson/view/RCI/job/rci-grayson/ws/pylint.html)

Automated unit test output can be seen in the build log. Tests currently focus on Pegasus DAX generation. PhantomJS is also used to test the user interface.

