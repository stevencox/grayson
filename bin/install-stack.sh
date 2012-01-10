#!/bin/bash

source $(dirname $0)/environment.sh

log=grayson-install.log

clean=0

unset installdir

for arg in $*; do
    case $arg in
	--installdir\=*)  installdir=$(echo $arg | sed s,--installdir=,,);;
	--clean)          clean=1;
    esac
done

if [ -z "$installdir" ]; then
    installdir=$GRAYSON_HOME/stack
    echo installing to $installdir
fi

date > $log
if [ $clean -eq 1 ]; then
    install_clean > $log 2>&1
fi
date >> $log
install_all >> $log 2>&1

exit 0