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

###############################################################################
#  This is a script that does the following:
#  * Pull madlib/postgres_9.6:latest from docker;
#  * Mount your local madlib directory to docker container;
#  * Build madlib from source; build dir is /madlib/build_docker which 
#    is mounted to your local madlib dir
#  * Install madlib and run install check;
#  * Log in to docker container from shell as postgres user, so that you
#    can run psql and start using madlib from here
#
# Note: you have to run this script from one level up from your madlib 
# directory, for example, ~/workspace which has madlib src directory there
###############################################################################
set -o pipefail

workdir=$(pwd)
user_name=$(whoami)
reponame="$(basename $(pwd))"

echo "======================================================================"
echo "Build user: ${user_name}"
echo "Work directory: ${workdir}"
echo "Git reponame: ${reponame}"
echo "======================================================================"

if [[ -z "${container_name}"]]; then
	container_name = madlib
fi

if [[ -z "${image_tag}"]]; then
	image_tag = latest
fi

if [[ ! -d "${workdir}/${reponame}" ]]; then
  echo "Error: you have to run this script from one level up from your madlib \
        directory, for example, ~/workspace which has madlib src directory \
        there"
  exit
fi

rm -rf build_docker_logs
mkdir build_docker_logs

echo "-----------creating docker container madlib--------------------"
docker kill "${container_name}"
docker rm "${container_name}"

# Pull down the base docker images
echo "Creating docker container"
docker pull madlib/postgres_9.6:"${image_tag}"

# Launch docker container with volume mounted from workdir
docker run -d --name "${container_name}" -v "${workdir}":/"${reponame}" \
 					madlib/postgres_9.6 | tee build_docker_logs/docker_setup.log

## This sleep is required since it takes a couple of seconds for the docker
## container to come up, which is required by the docker exec command that 
## follows.
sleep 5

echo "---------- Building MADlib -----------"
# cmake, make, make install
# The build folder is /madlib/build_docker, which is mounted to your local
# madlib repo
docker exec "${container_name}" bash -c "rm -rf /madlib/build_docker; \
							mkdir /madlib/build_docker; \
							cd /madlib/build_docker; \
							cmake ..; make; make install" \
			| tee "${workdir}/build_docker_logs/madlib_compile.log"

echo "---------- Installing and running install-check --------------------"
# Install MADlib and run install check
docker exec "${container_name}" bash -c "/madlib/build_docker/src/bin/madpack -p postgres \
							 -c postgres/postgres@localhost:5432/postgres \
							 install" \
			| tee "${workdir}/build_docker_logs/madlib_install.log"

docker exec "${container_name}" bash -c "/madlib/build_docker/src/bin/madpack -p postgres \
							-c postgres/postgres@localhost:5432/postgres \
							install-check" \
			| tee "${workdir}/build_docker_logs/madlib_install_check.log"

# To run psql, you have to login as postgres, not root
echo "---------- docker exec image as user postgres-----------"
docker exec "${container_name}" bash -c 'chown -R postgres:postgres /madlib/build_docker'
docker exec "${container_name}" bash -c 'chown -R postgres:postgres /madlib'
docker exec --user=postgres -it "${container_name}" bash \
		| tee "${workdir}/build_docker_logs/docker_exec.log"
