#!/bin/bash -l

# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

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

        gppkg -i madlib-*.gppkg

        $GPHOME/madlib/bin/madpack -s madlib -p greenplum -c localhost:\${PGPORT}/postgres install
        $GPHOME/madlib/bin/madpack -s madlib -p greenplum -c localhost:\${PGPORT}/postgres install-check | tee IC_gpdb5.0.out
        if grep -q "|FAIL|" IC_gpdb5.0.out; then
            echo "FAIL"
            false
            exit 1
        fi

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