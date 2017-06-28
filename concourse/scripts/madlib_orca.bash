#!/bin/bash -l

set -eox pipefail

source "./gpdb_src/concourse/scripts/common.bash"
CWDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

function prepare_madlib(){

    chown -R gpadmin:gpadmin ./madlib_src
    chown -R gpadmin:gpadmin ./madlib_gppkg
    cat > /opt/run_test.sh <<-EOF
        set -exo pipefail
		base_path=\${1}
		source /usr/local/greenplum-db-devel/greenplum_path.sh
		source \${base_path}/gpdb_src/gpAux/gpdemo/gpdemo-env.sh

        cd /tmp/
        wget https://cmake.org/files/v3.5/cmake-3.5.2-Linux-x86_64.tar.gz

        tar -xzvf cmake-3.5.2-Linux-x86_64.tar.gz
        cd cmake-3.5.2-Linux-x86_64/bin
        export CMAKE_HOME=\$(pwd)

        cd \${base_path}/madlib_src
        mkdir build1
        cd build1
        \${CMAKE_HOME}/cmake .. -DCMAKE_BUILD_TYPE=Release

        #Fixing gppkg issue with 5 -> 5.0
        sed -i.bak 's/GPDBVersion: 5/GPDBVersion: 5.0/g' ./deploy/gppkg/5/gppkg/gppkg_spec.yml

        make
        echo 'y' | ./src/bin/madpack -p greenplum -c localhost:\${PGPORT}/postgres install
        ./src/bin/madpack -p greenplum -c localhost:\${PGPORT}/postgres install-check
        make package
        make gppkg
        cp ./deploy/gppkg/5/madlib-ossv1.11_pv1.9.8_gpdb5-rhel5-x86_64.gppkg \${base_path}/madlib_gppkg/
	EOF

	chmod a+x /opt/run_test.sh
}

function setup_gpadmin_user() {
    ./gpdb_src/concourse/scripts/setup_gpadmin_user.bash "$TEST_OS"
}

function _main() {

    configure
    install_gpdb
    setup_gpadmin_user
    make_cluster
    prepare_madlib
    run_test
}

_main "$@"