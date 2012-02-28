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
    source $GRAYSON_HOME/bin/grayson-install-lib
    if [ -f $GRAYSON_VENV/bin/activate ]; then
	source $GRAYSON_VENV/bin/activate
    fi
fi

