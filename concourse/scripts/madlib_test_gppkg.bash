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
		# source /opt/gcc_env.sh
		source \${base_path}/gpdb_src/gpAux/gpdemo/gpdemo-env.sh

        cd \${base_path}/madlib_gppkg/

        gppkg -i madlib-ossv1.11_pv1.9.8_gpdb5-rhel5-x86_64.gppkg

        $GPHOME/madlib/bin/madpack -s madlib -p greenplum -c localhost:\${PGPORT}/postgres install
        $GPHOME/madlib/bin/madpack -s madlib -p greenplum -c localhost:\${PGPORT}/postgres install-check

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