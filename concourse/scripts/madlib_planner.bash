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

CWDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "${CWDIR}/madlib_common.bash"

function disable_orca(){
    cat > /opt/disable_orca.sh <<-EOF
        set -exo pipefail
        base_path=\${1}
        source /usr/local/greenplum-db-devel/greenplum_path.sh
        source \${base_path}/gpdb_src/gpAux/gpdemo/gpdemo-env.sh
        psql postgres -c "ALTER DATABASE postgres SET OPTIMIZER = OFF;"
EOF

    chmod a+x /opt/disable_orca.sh
    su - gpadmin -c "bash /opt/disable_orca.sh $(pwd)"

}

function _main() {

    configure
    install_gpdb
    setup_gpadmin_user
    make_cluster
    disable_orca
    prepare_madlib
    run_test
}

_main "$@"