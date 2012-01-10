#!/bin/bash

input=$1

mkdir check-dir

tar xvzf ../$input

cd ..

rm -rf check-dir

exit 0



