#!/bin/bash                                                                                                                                                                                          

set -e
set -x

if [ "$#" -ne 2 ]; then
    usage "$0 <version>"
    exit 1
fi

version=$1
env=$2

version_dir=v$version
rm -rf $version_dir
mkdir -p $version_dir
cd $version_dir

wget --no-check-certificate https://ci-dev.renci.org/nexus/service/local/repositories/renci-release/content/org/renci/grayson/$version/graysond-$version.tar.gz
tar xvzf graysond-$version.tar.gz
if [ ! -f conf/$env.conf ]; then
    echo $env is not a valid environment.
    exit 1
fi
mv conf/$env.conf conf/grayson.conf

GRAYSON_HOME=$PWD
. bin/setup.sh

grayson-install --frozen

#cd event
#install_nodelibs
#cd ..

cd ..
rm current
ln -s $version_dir current

cd current

exit 0