#!/bin/bash

set -e
set -x

export PATH=$PEGASUS_HOME/bin:$PATH
app_home=/home/scox/dev/grayson/samples/padcswan
data=/projects/sea_level_rise/OSG
outputs=$app_home/work/outputs
    
padcswan_log () {
    echo "   --(padcswan) $*"
}
padcswan_package () {

    touch binaries.tar.gz
    touch matrix.tar.gz

    # configure test
    echo test > $data/test/matrix.tar.gz
    tar cvzf \
	$data/test/binaries.tar.gz \
	--directory=$app_home/bin/test \
	padcswan.sh
    cp $app_home/bin/test/padcswan.sh $data/test/padcswan.sh

    # compress wind files
    cd $data/winds
    for wind_file in *.22; do
	padcswan_log "compressing wind file: $wind_file"
	tar czf $wind_file.tar.gz $wind_file

	#echo random > $outputs/random
	#tar czf $outputs/$wind_file.tar.gz--1-out.tar.gz $outputs/random

    done

    # stage executable
    cp $app_home/bin/pegaswan.sh $data/pegaswan.sh
    cp $app_home/bin/pegaswan.sh /var/www/html/padcirc/pegaswan.sh

}
padcswan_package $*




