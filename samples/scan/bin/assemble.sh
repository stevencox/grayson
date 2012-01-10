#!/bin/bash

set -e

echo "====================="
echo "== A S S E M B L E =="
echo "====================="
echo $0: $*

set -x

input=$1
outputdir=$2
mkdir -p $outputdir

output=$(echo $input | sed s,iprscan,sif,)

echo sif-data > $outputdir/$output

exit 0
