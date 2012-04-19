#!/bin/bash

set -e
set -x

echo $0: $*

input=$1

output=$(echo $input | sed s,fasta,iprscan,)

touch $output

exit 0
