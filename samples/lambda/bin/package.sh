#!/bin/bash

set -e
set -x

lambda_log () {
    echo "   --(lambda-package) $*"
}
lambda_package () {
    touch input-one.tar.gz
    touch input-two.tar.gz
}
lambda_package $*


exit 0

