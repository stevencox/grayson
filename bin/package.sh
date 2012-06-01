#!/bin/bash 

echo "====================================="
echo "==  P A C K A G E   G R A Y S O N  =="
echo "====================================="

set -e
set -x

version=0.1.0

tar cvzf grayson-sdk-$version.tar.gz bin lib/python lib/python/grayson samples \
    --exclude=.svn                                                 \
    --exclude=lib/python/grayson/debug                             \
    --exclude=samples/amber                                        \
    --exclude=samples/osg                                          \
    --exclude=samples/padcswan                                     \
    --exclude=*~

cp grayson-sdk-$version.tar.gz web/graysonapp/static/grayson-sdk.tar.gz

rm -rf web/static
mkdir web/static
echo yes | web/manage.py collectstatic 

tar czf graysond-$version.tar.gz bin lib web event conf  \
    --exclude=.svn                                       \
    --exclude=data/workflows                             \
    --exclude=web/logs                                   \
    --exclude=*~

artifact_dir=~/.m2/repository/org/renci/grayson/$version
mkdir -p $artifact_dir

cp graysond-$version.tar.gz $artifact_dir
cp grayson-sdk-$version.tar.gz $artifact_dir
cp bin/install.sh $artifact_dir 

exit 0