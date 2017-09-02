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
#  This is a script that does the following:
#  * Pull madlib/postgres_9.6:latest from docker;
#  * Mount your local madlib directory to docker container;
#  * Build madlib from source;
#  * Install madlib and run install check;
#  * Log in to docker container from shell as postgres user, so that you
#    can run psql and start using madlib from here
#
# Note: you have to run this script from one level up from your madlib directory, for
# example, ~/workspace which has madlib src directory there
#####################################################################################
set -o pipefail

workdir=`pwd`
user_name=`whoami`
reponame=madlib

echo "======================================================================"
echo "Build user: $user_name"
echo "Work directory: $workdir"
echo "Git reponame: $reponame"
echo "======================================================================"
echo "ls -la"
ls -la
echo "rm -rf logs"
rm -rf logs
echo "mkdir logs"
mkdir logs

echo "-----------creating docker container madlib--------------------"
echo "docker kill madlib"
docker kill madlib-test
echo "docker rm madlib"
docker rm madlib-test

# Pull down the base docker images
echo "Creating docker container"
docker pull madlib/postgres_9.6:latest

# Launch docker container with volume mounted from workdir
echo "-------------------------------"
cat <<EOF
docker run -d --name madlib-test -v "${workdir}/${reponame}":/madlib madlib/postgres_9.6 | tee logs/docker_setup.log
EOF
docker run -d --name madlib-test -v "${workdir}/${reponame}":/madlib madlib/postgres_9.6 | tee logs/docker_setup.log
echo "-------------------------------"


## This sleep is required since it takes a couple of seconds for the docker
## container to come up, which is required by the docker exec command that follows.
sleep 5

echo "---------- Building MADlib -----------"
# cmake, make, make install
cat <<EOF
docker exec madlib bash -c 'rm -rf /build; mkdir /build; cd /build; cmake ../madlib; make clean; make; make install' | tee $workdir/logs/madlib_compile.log
EOF
docker exec madlib-test bash -c 'rm -rf /build; mkdir /build; cd /build; cmake ../madlib; make clean; make; make install' | tee $workdir/logs/madlib_compile.log

echo "---------- Installing and running install-check --------------------"
# Install MADlib and run install check
cat <<EOF
docker exec madlib bash -c '/build/src/bin/madpack -p postgres -c postgres/postgres@localhost:5432/postgres install' | tee $workdir/logs/madlib_install.log
EOF
docker exec madlib-test bash -c '/build/src/bin/madpack -p postgres -c postgres/postgres@localhost:5432/postgres install' | tee $workdir/logs/madlib_install.log

cat <<EOF
docker exec madlib bash -c 'mkdir -p /tmp'
docker exec madlib bash -c '/build/src/bin/madpack -p postgres  -c postgres/postgres@localhost:5432/postgres -d /tmp install-check' | tee $workdir/logs/madlib_install_check.log
EOF

docker exec madlib-test bash -c 'mkdir -p /tmp'
docker exec madlib-test bash -c '/build/src/bin/madpack -p postgres  -c postgres/postgres@localhost:5432/postgres -d /tmp install-check' | tee $workdir/logs/madlib_install_check.log

# To run psql, you have to login as postgres, not root
echo "---------- docker exec image as user postgres-----------"
cat <<EOF
docker exec -it --user=postgres madlib bash | tee $workdir/logs/docker_exec.log
EOF
docker exec --user=postgres -it madlib-test bash | tee $workdir/logs/docker_exec.log
