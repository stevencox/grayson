#!/bin/bash

set -x
set -e

mkdir -p delta-files

iterations=$1
output=$2

for x in $(seq 0 $iterations); do

    echo data-$x > delta-files/$x.txt

done

cd delta-files

tar cvf $output *
cp *tar.gz ..

cd ..
rm -rf delta-files

exit 0


