#!/bin/bash

set -x
set -e

file=$1
slice=$2

lambda () {
    echo ============================================================================================================
    echo $0 $*
    ls -lisa
    echo ============================================================================================================
}

lambda > $file-$slice-out.tar.gz

sleep 2

exit 0
