#!/bin/bash

set -e
set -x

date

pwd

echo host: $(hostname -f)

APP_HOME=${PWD}
GET_FLAGS="--no-check-certificate --quiet"
namdType=multicore
runLength=100

getarg () {
    echo $1 | sed s,.*=,,
}
stage_in () { # for non-pegasus scenarios including glideinwms and testing.
    echo Unpack and configure mpich2 MPI libraries.
    wget ${GET_FLAGS} https://ci-dev.renci.org/nexus/service/local/repo_groups/Autobuild-RENCI/content/org/renci/mpich2-static/1.1.1p1/mpich2-static-1.1.1p1.tar.gz
    echo Unpack and configure NAMD
    wget ${GET_FLAGS} https://ci-dev.renci.org/nexus/service/local/repo_groups/Autobuild-RENCI/content/org/renci/namd/2.8-linux-x86_64-${namdType}/namd.tar.gz
    echo Unpack and configure input files
    wget ${GET_FLAGS} https://ci-dev.renci.org/nexus/service/local/repo_groups/Autobuild-RENCI/content/org/renci/duke/chemistry/beratan-0.tar.gz
}
configure_components () {
    echo Configure MPICH2...
    tar xzf mpich2-static-1.1.1p1.tar.gz
    MPIEXEC=mpich2/mpiexec.gforker
    chmod +x ${MPIEXEC}
    echo Configure NAMD...
    tar xzf namd.tar.gz 
    NAMD_HOME=${APP_HOME}/$(ls -1 | grep NAMD_)
    export LD_LIBRARY_PATH=${NAMD_HOME}:$LD_LIBRARY_PATH
    NAMD_EXE=${NAMD_HOME}/namd2
    chmod +x ${NAMD_EXE} 
    echo Configure cpuinfo...
    chmod +x ./cpuinfo
    echo Configure data...
    tar xvzf beratan-0.tar.gz
}
configure_run () {
    echo Editing NAMD configuration file...
    # https://research.cchmc.org/wiki/index.php/NAMD_Tutorial#Restarting_.28continuing.29_simulation
    local last=$(( slice - 1 ))
    local restart=out-$last.tar.gz
    if [ -f "$restart" ]; then
	echo Extracting restart data...
	cd RENCI
	tar xvzf ../$restart
	cd ..
	echo Configuring for restart...
	#grep -v "set temperature" RENCI/$config.conf |                      \
	grep -v "reinitvels" RENCI/$config.conf |                            \
	    sed                                                              \
	    -e "s,set inputname .*,set inputname      $model-$last,"         \
	    -e "s,binCoordinates .*,binCoordinates     $model-$last.coor,"   \
	    -e "s,binVelocities .*,binVelocities      $model-$last.vel,"     \
	    -e "s,extendedSystem.*,extendedSystem     $model-$last.xsc,"   \
 	    > RENCI/$config.new
	mv RENCI/$config.new RENCI/$config.conf
    fi
    echo Edit NAMD configuration
    cat RENCI/$config.conf | sed                                \
	-e "s,^run .*,run ${runLength},"                        \
	-e "s,outputName .*,outputName         $model-$slice,"  \
	-e "s,^fullElectFrequency  .*,fullElectFrequency  2,"   \
        -e "s,^stepspercycle       .*,stepspercycle       20," > RENCI/$config.new
    mv RENCI/$config.new RENCI/$config.conf
    echo "Configuration edits:"
    egrep "set inputname|binCoordinates|binVelocities|extendedSystem|^run |outputName|" RENCI/$config.conf
}
execute_namd () {
    ls -lisa
    ls -lisa RENCI
    date
    local NAMD_ARGS=
    local CHARMRUN_ARGS
    if [ "x$namdType" == "xCUDA" ]; then
	NAMD_ARGS=+idlepoll
	core_count=2
	CHARMRUN_ARGS=++local
    else
	./cpuinfo
	local core_count=$( ./cpuinfo | awk '/physical CPUs:/ { printf "%5s * ", $5 } /cores per CPU:/ { print $6 }' | bc )
    fi
    #${MPIEXEC} -n ${core_count} ${NAMD_EXE} ${NAMD_ARGS} RENCI/$config.conf > RENCI/$config.log

    ${NAMD_HOME}/charmrun ${CHARMRUN_ARGS} +p8 ${NAMD_HOME}/namd2 +idlepoll RENCI/$config.conf > RENCI/$config.log

    EXIT_CODE=$?
    date

    cd RENCI
    contents=
    for extension in coor vel xsc; do
	if [ -f $model-$slice.$extension ]; then
	    contents="$contents $model-$slice.$extension"
	fi
    done
    tar cvzf ../out-$slice.tar.gz $contents $config.log $config.conf
    #rm *-$slice.*
    cd ..
}
clean_up () {
    rm -rf NAMD_*Linux* RENCI/ mpich2* namd.tar.gz beratan*
}
main () {
    local get=
    local cleanup=
    for arg in $*; do
	case $arg in
	    --model\=*)      model=$( getarg $arg );;
	    --slice\=*)      slice=$( getarg $arg );;
	    --config\=*)     config=$( getarg $arg );;
	    --namdType\=*)   namdType=$( getarg $arg );;
	    --runLength\=*)  runLength=$( getarg $arg );;
	    --outputname\=*) outputname=$( getarg $arg );;
	    --get)           get=true;;
	    --cleanup)       cleanup=true;;
        esac
    done
    if [ ! -z "$get" ]; then
	stage_in
    fi
    configure_components
    configure_run
    execute_namd
    if [ ! -z "$cleanup" ]; then
	clean_up
    fi
}
test_run () {
    for slice in 0 1 2; do
	main                                         \
	    --model=ternarycomplex119819             \
	    --config=ternarycomplex_popcwimineq-05   \
	    --slice=$slice                           \
	    --runLength=20
    done
}
main $*

exit $EXIT_CODE
