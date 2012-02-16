#set -x

if [ -z "$GRAYSON_HOME" ]; then
   echo error: GRAYSON_HOME must be set.
else
    export PYTHONPATH=${GRAYSON_HOME}/lib/python:${PYTHONPATH}
    export PATH=${GRAYSON_HOME}/bin:${PATH}
    chmod +x $GRAYSON_HOME/bin/*
    if [ -z "$installdir" ]; then
	export installdir=$GRAYSON_HOME/stack
    fi
    #. $GRAYSON_HOME/bin/environment.sh    
    source $GRAYSON_HOME/bin/grayson-install-lib   
    grayson-install-initialize
    $GRAYSON_VENV/bin/activate
fi

