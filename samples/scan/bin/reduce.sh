#!/bin/bash

set -e

echo "================="
echo "== R E D U C E =="
echo "================="
echo $0: $*
echo reduce: $*

set -x

outputdir=$1

output=full-sifs.txt

echo > $output
for output in $outputdir/sif*; do
    echo sif-chunk: >> $output
done

exit 0
