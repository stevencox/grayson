#!/bin/bash

echo merge $*
ls -lisa > report.txt
date >> report.txt
pwd >> report.txt
find . >> report.txt
