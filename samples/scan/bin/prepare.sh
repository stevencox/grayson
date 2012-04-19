#!/bin/bash

set -e

echo "===================="
echo "== P R E P A R E  =="
echo "===================="
echo $0: $*

set -x

input=$1
output=$2
outputdir=$3
mkdir -p $outputdir

echo > $output

mkdir scratch
cd scratch

c=0
for row in $(cat ../$input); do
    echo "$c $c" >> fasta-$c.txt
    c=$(( c + 1 ))
done

tar cvzf ../$output fasta-*.txt

cd ..

rm -rf scratch

exit 0
