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

function prepare_madlib(){

    chown -R gpadmin:gpadmin ./madlib_src
    cat > /opt/run_test.sh <<-EOF
        set -exo pipefail
		base_path=\${1}
		source /usr/local/greenplum-db-devel/greenplum_path.sh
		source \${base_path}/gpdb_src/gpAux/gpdemo/gpdemo-env.sh
        psql postgres -c "SHOW OPTIMIZER;"
        cd /tmp/
        wget https://cmake.org/files/v3.5/cmake-3.5.2-Linux-x86_64.tar.gz

        tar -xzf cmake-3.5.2-Linux-x86_64.tar.gz
        cd cmake-3.5.2-Linux-x86_64/bin
        export CMAKE_HOME=\$(pwd)

        cd \${base_path}/madlib_src
        mkdir build1
        cd build1
        \${CMAKE_HOME}/cmake .. -DCMAKE_BUILD_TYPE=Release

        make
        echo 'y' | ./src/bin/madpack -p greenplum -c localhost:\${PGPORT}/postgres install
        ./src/bin/madpack -p greenplum -c localhost:\${PGPORT}/postgres install-check | tee IC_gpdb5.0.out
        if grep -q "|FAIL|" IC_gpdb5.0.out; then
            echo "FAIL"
            false
            exit 1
        fi

	EOF

	chmod a+x /opt/run_test.sh
}

function create_gppkg(){

    cat > /opt/create_gppkg.sh <<-EOF
        set -exo pipefail
        base_path=\${1}
        source /usr/local/greenplum-db-devel/greenplum_path.sh
        source \${base_path}/gpdb_src/gpAux/gpdemo/gpdemo-env.sh

        cd \${base_path}/madlib_src/build1

        #Fixing gppkg issue with 5 -> 5.0
        sed -i.bak 's/GPDBVersion: 5/GPDBVersion: 5.0/g' ./deploy/gppkg/5/gppkg/gppkg_spec.yml

        make package
        make gppkg
        cp ./deploy/gppkg/5/madlib-*.gppkg \${base_path}/madlib_gppkg/
EOF

    chmod a+x /opt/create_gppkg.sh
    su - gpadmin -c "bash /opt/create_gppkg.sh $(pwd)"

}

function setup_gpadmin_user() {
    ./gpdb_src/concourse/scripts/setup_gpadmin_user.bash "$TEST_OS"
}
