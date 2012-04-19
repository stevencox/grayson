#!/bin/bash

echo score.x

echo database > database.txt
echo matrix > matrix.txt
echo adjacency > adjacency.txt

cat *.txt
pwd
grep -cn "." *.txt
ls -lisa

exit 0

