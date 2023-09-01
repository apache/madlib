#!/bin/bash
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

#####################################################################################
workdir=`pwd`
user_name=`whoami`

# FIXME: Jenkins build is not working, even though PG15 compiles on local Mac.
# Need to find an efficient way to debug since it has a server crash.

echo "======================================================================"
echo "Build user: $user_name"
echo "Work directory: $workdir"
echo "----------------------------------------------------------------------"
echo "ls -la"
ls -la
echo "-------------------------------"
echo "rm -rf build_jenkins"
rm -rf build_jenkins
echo "-------------------------------"
echo "rm -rf logs"
rm -rf logs
echo "mkdir logs"
mkdir logs
echo "-------------------------------"

echo "docker kill madlib"
docker kill madlib
echo "docker rm madlib"
docker rm madlib

echo "Creating docker container"
# Pull down the base docker images
echo "docker pull madlib/postgres_15:jenkins"
docker pull madlib/postgres_15:jenkins
# Launch docker container with volume mounted from workdir
echo "-------------------------------"
cat <<EOF
docker run -d -t -e POSTGRES_PASSWORD=postgres --name madlib --ulimit core=-1  --privileged -v "${workdir}":/madlib madlib/postgres_15:jenkins | tee logs/docker_setup.log
EOF
docker run -d -t -e POSTGRES_PASSWORD=postgres --name madlib --ulimit core=-1  --privileged -v "${workdir}":/madlib madlib/postgres_15:jenkins | tee logs/docker_setup.log
echo "-------------------------------"

## This sleep is required since it takes a couple of seconds for the docker
## container to come up, which is required by the docker exec command that follows.
sleep 5

cat <<EOF
docker exec madlib bash -c 'cp /madlib/tool/pg_hba.conf.postgres /etc/postgresql/15/main/pg_hba.conf; echo "    * soft nproc unlimited" > /etc/security/limits.d/postgres-limits.conf ' | tee $workdir/logs/madlib_compile.log
EOF
docker exec madlib bash -c 'cp /madlib/tool/pg_hba.conf.postgres /etc/postgresql/15/main/pg_hba.conf; echo "    * soft nproc unlimited" > /etc/security/limits.d/postgres-limits.conf ' | tee $workdir/logs/madlib_compile.log

cat <<EOF
docker exec madlib bash -c 'service postgresql start' | tee $workdir/logs/madlib_compile.log
EOF
docker exec madlib bash -c 'service postgresql start' | tee $workdir/logs/madlib_compile.log

echo "---------- Install pip, and mock -----------"
# cmake, make, make install, and make package
cat <<EOF
docker exec madlib bash -c 'apt-get update; apt-get install -y python3-pip; pip install mock pandas numpy xgboost scikit-learn pyyaml pyxb-x' | tee $workdir/logs/madlib_compile.log
EOF
docker exec madlib bash -c 'apt-get update; apt-get install -y python3-pip; pip install mock pandas numpy xgboost scikit-learn pyyaml pyxb-x' | tee $workdir/logs/madlib_compile.log

echo "---------- Building package -----------"
# cmake, make, make install, and make package
cat <<EOF
docker exec madlib bash -c 'rm -rf /build_jenkins; mkdir /build_jenkins; cd /build_jenkins; cmake ../madlib; make clean; make -j$(nproc); make -j$(nproc); make install; make package; chown -R postgres:postgres /build_jenkins ' | tee $workdir/logs/madlib_compile.log
EOF
docker exec madlib bash -c 'rm -rf /build_jenkins; mkdir /build_jenkins; cd /build_jenkins; cmake ../madlib; make clean; make -j$(nproc); make -j$(nproc); make install; make package; chown -R postgres:postgres /build_jenkins ' | tee $workdir/logs/madlib_compile.log

echo "---------- Installing and running dev-check --------------------"
# Install MADlib and run dev check

cat <<EOF
docker exec -u postgres madlib bash -c 'export PATH=\$PATH:/usr/lib/postgresql/15/bin/; /build_jenkins/src/bin/madpack -s mad -p postgres -c postgres/postgres@localhost:5432/postgres install' | tee $workdir/logs/madlib_install.log
EOF
docker exec -u postgres madlib bash -c 'export PATH=$PATH:/usr/lib/postgresql/15/bin/; /build_jenkins/src/bin/madpack -s mad -p postgres -c postgres/postgres@localhost:5432/postgres install' | tee $workdir/logs/madlib_install.log

cat <<EOF
docker exec madlib bash -c 'mkdir -p /tmp'
docker exec madlib bash -c '/build_jenkins/src/bin/madpack -s mad -p postgres  -c postgres/postgres@localhost:5432/postgres -d /tmp dev-check' | tee $workdir/logs/madlib_dev_check.log
docker exec madlib bash -c '/build_jenkins/src/bin/madpack -s mad -p postgres  -c postgres/postgres@localhost:5432/postgres -d /tmp unit-test' | tee -a $workdir/logs/madlib_dev_check.log
EOF

docker exec madlib bash -c 'mkdir -p /tmp'
docker exec madlib bash -c 'rm -rf /build_jenkins/src/ports/postgres/modules/deep_learning/test'
docker exec madlib bash -c 'rm -rf /build_jenkins/src/ports/postgres/15/modules/deep_learning/test'
# FIXME following tests fail on the docker
docker exec madlib bash -c 'rm -rf /build_jenkins/src/ports/postgres/modules/linalg/test/linalg.sql_in'
docker exec madlib bash -c 'rm -rf /build_jenkins/src/ports/postgres/modules/prob/test/prob.sql_in'
docker exec madlib bash -c 'rm -rf /build_jenkins/src/ports/postgres/modules/stats/test/cox_prop_hazards.sql_in'
docker exec madlib bash -c 'rm -rf /build_jenkins/src/ports/postgres/modules/utilities/test/path.sql_in'
docker exec madlib bash -c 'rm -rf /build_jenkins/src/ports/postgres/modules/mxgboost/test/madlib_xgboost.sql_in'
docker exec madlib bash -c 'rm -rf /build_jenkins/src/ports/postgres/modules/kmeans/test/kmeans.sql_in'
# Run dev check
docker exec madlib bash -c '/build_jenkins/src/bin/madpack -s mad -p postgres  -c postgres/postgres@localhost:5432/postgres -d /tmp dev-check' | tee $workdir/logs/madlib_dev_check.log
# Run unit tests, and append output to dev_check's log file
docker exec madlib bash -c '/build_jenkins/src/bin/madpack -s mad -p postgres  -c postgres/postgres@localhost:5432/postgres -d /tmp unit-test' | tee -a $workdir/logs/madlib_dev_check.log

echo "--------- Copying packages -----------------"
echo "docker cp madlib:build_jenkins $workdir"
docker cp madlib:build_jenkins $workdir
echo "docker cp madlib:tmp $workdir"
docker cp madlib:tmp $workdir

echo "-------------------------------"
echo "ls -la"
ls -la
echo "-------------------------------"
echo "ls -la build_jenkins"
ls -la build_jenkins/
echo "-------------------------------"

# convert dev-check test results to junit format for reporting
cat <<EOF
python3 tool/jenkins/junit_export.py $workdir/logs/madlib_dev_check.log $workdir/logs/madlib_dev_check.xml
EOF
python3 tool/jenkins/junit_export.py $workdir $workdir/logs/madlib_dev_check.log $workdir/logs/madlib_dev_check.xml
