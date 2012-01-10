#!/bin/bash

echo alpha $*


if [ "$1" == "-in" ]; then
    input=$2
    shift
    shift
fi

if [ "$1" == "-out" ]; then
    output=$2
    shift
    shift
    touch $output
fi

exit 0


