

# sudo yum -y install libcurl-devel gcc gcc-c++ autoconf automake \
#                     python-devel openldap-devel openssl-devel   \
#                     python-setuptools erlang rabbitmq sqlite-devel \
#                     condor
# sudo easy_install virtualenv
# virtualenv --no-site-packages mycoolproject -p python2.7
# easy_install pycurl python-ldap django-celery pika
# sudo rpm -vi ~/Downloads/rabbitmq-server-2.4.1-1.noarch.rpm
# install_node
# install_socketio

# condor:
# ensure hostname is set.
# edit condor_config:
#    HOSTALLOW_WRITE = (...), *.renci.org, 127.0.0.1

# chkconfig rabbitmq-server on 
# /sbin/service rabbitmq-server start


#set -e
#set -x

# prerequisites:
#  apt-get: libldap2-dev libsasl2-dev libssl-dev libcurl3-openssl-dev curl

#export PEGASUS_HOME=$(dirname $(dirname $(which pegasus-plan)))
python_version=2.7.1
releases='http://www.renci.org/~scox/bin'

dirs="apache modwsgi compressor python erlang rabbitmq node django sqlite pegasus java"
if [ "$(uname -a | grep -c Darwin)" -eq 1 ]; then
    export FQDN=0.0.0.0 #$(hostname)
else
    export FQDN=$(hostname -f)
fi
ensure_dirs_exist () {
    for dir in $dirs; do
	mkdir -p $installdir/$dir
    done
}
install_clean () {
    cd $installdir
    for dir in $dirs; do
	echo "deleting dir: $dir"
	rm -rf $installdir/$dir
    done
    ensure_dirs_exist
}

path_prepend () {
    element=$1
    if [ "$(echo $PATH | grep -c $element)" -eq "0" ]; then
	export PATH=$element:$PATH
    fi
}
ldpath_prepend () {
    element=$1
    if [ "$(echo $LD_LIBRARY_PATH | grep -c $element)" -eq "0" ]; then
	export LD_LIBRARY_PATH=$element:$LD_LIBRARY_PATH
    fi
}
log () {
    echo $*
}

install_app () {
    name=$1
    version=$2
    dir=$3$version
    archive=$dir.tar.gz
    src=$4/$archive
    clean=$5
    cd $installdir/$name
    wget -q $src
    tar xzf $archive
    cd $dir
    ./configure --prefix=$installdir/$name
    make
    make install
}


install_apache () {
    log "installing apache"
    apache_version=2.2.19
    apache_archive=httpd-$apache_version.tar.gz
    apache_src=$releases/$apache_archive
    cd $installdir/apache
    wget -q $apache_src
    tar xvzf $apache_archive
    cd httpd-$apache_version
    ./configure --prefix=$installdir/apache
    make
    make install
}
setup_apache () {
    export APACHE_HOME=$installdir/apache
    path_prepend $APACHE_HOME/bin
}

install_sqlite () {
    cd $installdir
    sqlite_version=3070602
    sqlite_archive=sqlite-autoconf-$sqlite_version.tar.gz
    sqlite_src=http://www.sqlite.org/$sqlite_archive
    cd $installdir/sqlite
    wget -q $sqlite_src
    tar xvzf $sqlite_archive
    cd sqlite-autoconf-$sqlite_version
    ./configure --prefix=$installdir/sqlite
    make
    make install
}
setup_sqlite () {
    export SQLITE_HOME=$installdir/sqlite
    export PATH=$SQLITE_HOME/bin:$PATH
    export LD_LIBRARY_PATH=$SQLITE_HOME/.libs:$LD_LIBRARY_PATH
}

install_python () {
    cd $installdir
    log "installing python"
    python_archive=Python-$python_version.tgz
    python_src=$releases/$python_archive
    cd $installdir/python 
    wget -q $python_src
    tar xvzf $python_archive
    cd Python*
    ./configure \
	--prefix=$installdir/python \
	--enable-shared
    make
    make install
}
setup_python () {
    export PYTHON_HOME=$installdir/python
    path_prepend $PYTHON_HOME
    path_prepend $PYTHON_HOME/bin
    ldpath_prepend $PYTHON_HOME/lib
}

install_modwsgi () {
    modwsgi_version=3.3
    modwsgi_archive=mod_wsgi-$modwsgi_version.tar.gz
    modwsgi_src=$releases/$modwsgi_archive
    cd $installdir/modwsgi
    wget -q $modwsgi_src
    tar xzf $modwsgi_archive
    cd mod_wsgi-$modwsgi_version
    ./configure \
	--with-python=$PYTHON_HOME/bin/python \
	--with-apxs=$APACHE_HOME/bin/apxs
    make
    make install
    set +x
}

install_python_ldap () {
    python_ldap_version=2.3.13
    python_ldap_archive=python-ldap-$python_ldap_version.tar.gz
    python_ldap_src=$releases/$python_ldap_archive
    cd $installdir/python
    wget -q $python_ldap_src
    tar xvzf $python_ldap_archive
    cd python-ldap-$python_ldap_version
    python setup.py build
    python setup.py install
}

install_celery () {
    celery_version=2.2.7
    celery_archive=django-celery-$celery_version.tar.gz
    celery_src=$releases/$celery_archive
    cd $installdir/python
    wget -q $celery_src
    tar xvzf $celery_archive
    cd django-celery-$celery_version
    python setup.py build
    python setup.py install
}
install_epydoc () {
    epydoc_version=3.0.1
    epydoc_archive=epydoc-$epydoc_version.tar.gz
    epydoc_src=$releases/$epydoc_archive
    cd $installdir
    wget -q $epydoc_src
    tar xvzf $epydoc_archive
    cd epydoc-$epydoc_version
    python setup.py build install
}

install_easy_install () {
    setup_python
    setup_easy_install
    easy_install_version=0.6c11
    easy_install_archive=setuptools-$easy_install_version-py2.7.egg
    easy_install_src=$releases/$easy_install_archive
    cd $installdir/python/Python-2.7.1 
    wget -q $easy_install_src &&
    sh $easy_install_archive &&
    echo "installing python-ldap..." &&
    install_python_ldap &&
    echo "installing celery..." &&
    install_celery &&
    echo "installing pika AMQP library..." &&
    easy_install pika &&
    echo "installing python graph core" &&
    easy_install python-graph-core==1.8.0
}
setup_easy_install () {
    echo 
}
install_django () {
    django_version=1.3
    django_archive=Django-$django_version.tar.gz
    django_src=$releases/$django_archive
    cd $installdir/django
    wget -q $django_src
    tar xvzf Django-$django_version.tar.gz
    cd Django-$django_version
    python setup.py install
}

install_erlang () {
    erlang_version=R14B02
    erlang_archive=otp_src_$erlang_version.tar.gz
    erlang_src=http://www.erlang.org/download/$erlang_archive
    cd $installdir/erlang
    wget -q $erlang_src
    tar xvzf $erlang_archive
    cd otp_src_$erlang_version
    ./configure --prefix=$installdir/erlang
    make
    make install
    return 0
}
setup_erlang () {
    export ERLANG_HOME=$installdir/erlang
    path_prepend $ERLANG_HOME/bin
}

install_rabbitmq () {
    rabbitmq_archive=rabbitmq-server-$rabbitmq_version.tar.gz
    rabbitmq_src=http://www.rabbitmq.com/releases/rabbitmq-server/v2.4.1/$rabbitmq_archive
    cd $installdir/rabbitmq
    wget -q $rabbitmq_src
    tar xvzf $rabbitmq_archive
    cd rabbitmq-server-$rabbitmq_version
    make
    export TARGET_DIR=$installdir/rabbitmq
    export SBIN_DIR=$installdir/rabbitmq/sbin
    export MAN_DIR=$installdir/rabbitmq/man
    make install_bin # install also builds documentation, requiring xmlto
}
setup_rabbitmq () {
    rabbitmq_version=2.4.1
    export RABBIT_HOME=$installdir/rabbitmq/rabbitmq-server-$rabbitmq_version
    path_prepend $RABBIT_HOME/scripts
}
#-----------------------------------------
install_rabbitmq () {
    cd $installdir/rabbitmq
    wget $releases/rabbitmq-server-generic-unix-2.6.0.tar.gz
    tar xvzf rabbitmq-server-generic-unix-2.6.0.tar.gz
    
}
setup_rabbitmq () {
    rabbitmq_version=2.6.0
    export RABBIT_HOME=$installdir/rabbitmq/rabbitmq_server-$rabbitmq_version
    path_prepend $RABBIT_HOME/sbin
}

install_m2crypto () {
    m2crypto_version=0.21.1
    m2crypto_archive=M2Crypto-$m2crypto_version.tar.gz
    wget $releases/$m2crypto_archive
    
    tar xvzf $m2crypto_archive
    
    cat M2Crypto-$m2crypto_version/setup.py | sed \
	-e "s#\[opensslIncludeDir\]#[opensslIncludeDir, os.path.join \(opensslIncludeDir, 'openssl'\)]#" \
	> M2Crypto-$m2crypto_version/setup.py.new
    mv M2Crypto-$m2crypto_version/setup.py.new M2Crypto-$m2crypto_version/setup.py
    
    cd M2Crypto-$m2crypto_version
    
    python setup.py build install
}

install_node () {
    node_version=v0.4.7
    node_archive=node-$node_version.tar.gz
    node_src=$releases/$node_archive
    cd $installdir/node
    wget -q $node_src
    tar xvzf $node_archive
    cd node-$node_version
    ./configure --prefix=$installdir/node
    make
    make install
    install_npm
    install_nodelibs
}
install_npm () {
    cd $installdir/node
    curl $releases/node-install.sh | clean=no sh
}
setup_node () {
    export NODE_HOME=$installdir/node
    path_prepend $NODE_HOME/bin
}
install_nodelibs () {
    cd $GRAYSON_HOME/event/
    log "installing socket.io"
    npm install socket.io@0.7.7
    npm install amqp@0.0.2
}
install_nodelibs () {
    cd $GRAYSON_HOME/event/
    log "installing socket.io"
    npm install $releases/npm/socket.io-0.8.4.tar.gz
    npm install express@2.4.6
    npm install amqp@0.0.2
}

install_java () {
    java_archive=jdk${java_version}.tar.gz
    cd $installdir/java
    wget -q $releases/$java_archive
    tar xvzf $java_archive
}
setup_java () {
    java_version=1.6.0_25
    export JAVA_HOME=$installdir/java/jdk${java_version}
    path_prepend $JAVA_HOME/bin
}
install_pegasus () {
    pegasus_arch=x86_rhel_5
    if [ "$(uname -a | grep -c Darwin)" -eq 1 ]; then
	pegasus_arch=x86_64_macos_10.5
    fi
    pegasus_archive=pegasus-binary-${pegasus_version}-${pegasus_arch}.tar.gz
    cd $installdir/pegasus
    wget -q $releases/$pegasus_archive
    tar xvzf $pegasus_archive    
}
setup_pegasus () {
    pegasus_version=3.0.3
    export PEGASUS_HOME=$installdir/pegasus/pegasus-${pegasus_version}
    path_prepend $PEGASUS_HOME/bin
}

setup_compressor () {
    x=2
}
install_compressor () {
    compressor_version=1.0.1
    compressor_archive=django_compressor-$compressor_version.tar.gz
    cd $installdir/compressor &&
    wget $releases/$compressor_archive &&
    tar xvzf $compressor_archive
    cd django_compressor-$compressor_version &&
    python setup.py install
}
setup_all () {
    #set -x
    setup_python
    setup_apache
    setup_erlang
    setup_rabbitmq
    setup_node
    #setup_java
    setup_compressor
    #setup_pegasus
}
install_all () {
    mkdir -p $installdir &&
    ensure_dirs_exist &&
    if [ ! -f $installdir/python/* ]; then
	install_python 
    fi &&
    if [ ! -f $installdir/erlang/* ]; then
	install_erlang
    fi &&
    if [ ! -f $installdir/django/* ]; then
	install_django
    fi &&
    if [ ! -f $installdir/compressor/* ]; then
	install_compressor
    fi &&
    install_easy_install &&
    if [ ! -f $installdir/rabbitmq/* ]; then
	install_rabbitmq
    fi &&
    if [ ! -f $installdir/node/* ]; then
	install_node
    fi &&
    install_nodelibs 
}
install_all_clean () {
    rm -rf $installdir
    mkdir -p $installdir
    cd $installdir/..
    time install_clean > grayson-install.log 2>&1
    time install_all >> grayson-install.log 2>&1
}
setup_all



# job control
grayson_kill () {
    thing=$1
    ps -ef | grep $thing | grep -v grep
    pids=$(ps -ef | grep $thing | grep -v grep | awk '{print $2}')
    for pid in $pids; do
	if [ "$(echo $thing | grep -c rabbit)" -gt 0 ]; then 
	    sudo kill -9 $pid
	else
	    kill -9 $pid
	fi
    done
}











function deleteme () {
grayson_taskd () {
    cd $GRAYSON_HOME
    web/manage.py celeryd -l debug > $GRAYSON_HOME/web/logs/celeryd.log 2>&1 &
}
grayson_webd () {
    cd $GRAYSON_HOME
    web/manage.py runserver ${FQDN}:8000 > $GRAYSON_HOME/web/logs/web.log 2>&1
}
grayson_rabbitd () {
    sudo grayson-rabbit.sh #
}
grayson_eventd () {
    cd $GRAYSON_HOME/event
    sleep 5 # figure out if rabbit is started before launching node
    node server.js > $GRAYSON_HOME/var/logs/event.log 2>&1 &
}
grayson_stop () {
    grayson_kill celeryd
    grayson_kill manage.py
    grayson_kill "server.js"
    grayson_kill rabbitmq
}
grayson_noded () {
    cd event
    sleep 5 # figure out if rabbit is started before launching node
    node server.js > $GRAYSON_HOME/var/logs/event.log 2>&1 &
}
grayson_start_rabbit () {
    rabbitmq-server start -detached
}
grayson_start () {
    set -x
    cd $GRAYSON_HOME    
    sudo /root/graysoninit
    web/manage.py celeryd -l debug > $GRAYSON_HOME/var/logs/celeryd.log 2>&1 &
    cd event
    sleep 5 # figure out if rabbit is started before launching node
    node server.js > $GRAYSON_HOME/var/logs/event.log 2>&1 &
    cd $GRAYSON_HOME
    web/manage.py runserver ${FQDN}:8000 > $GRAYSON_HOME/web/logs/web.log 2>&1
    set +x
}
grayson_start () {
    set -x
    cd $GRAYSON_HOME
    grayson_rabbitd
    grayson_taskd
    grayson_eventd
    grayson_webd
    set +x
}
}
 




