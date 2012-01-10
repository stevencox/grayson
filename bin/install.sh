#!/bin/bash                                                                                                                                                                                          

set -e
set -x

if [ "$#" -ne 1 ]; then
    usage "$0 <version>"
    exit 1
fi

version=$1
version_dir=v$version
mkdir -p $version_dir
cd $version_dir
rm -rf ./*
wget --no-check-certificate https://ci-dev.renci.org/nexus/service/local/repositories/renci-release/content/org/renci/grayson/$version/graysond-$version.tar.gz
tar xvzf graysond-$version.tar.gz
mv conf/prod.conf conf/grayson.conf

GRAYSON_HOME=$PWD
installdir=/opt/grayson/stack
. bin/setup.sh

cd event
install_nodelibs
cd ..

cd ..
rm current
ln -s $version_dir current

exit 0