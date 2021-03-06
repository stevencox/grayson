#!/bin/bash                                                                                                                                                                                          
set -e
#set -x

if [ "$#" -ne 2 ]; then
    usage "$0 <GRAYSON_HOME> <GRAYSON_STACK>"
    exit 1
fi

GRAYSON_HOME=$1
installdir=$2
. $GRAYSON_HOME/bin/setup.sh

cd $GRAYSON_HOME
web/manage.py celeryd -l debug -f ../var/logs/tasks.log

exit 0
