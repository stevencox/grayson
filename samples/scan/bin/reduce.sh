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
for sif in $outputdir/sif*; do
    echo "-------------------------------" >> $output
    echo sif-chunk:[$sif]                  >> $output
    cat $sif                               >> $output 
    echo "-------------------------------" >> $output
done

exit 0
