#!/bin/bash

echo executing: $0 $*

ls -lisa > $0.output

tar cvzf output.tar.gz $0.output
