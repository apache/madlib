#!/bin/sh

#####################################################################################
### If this bash script is executed as a stand-alone file, assuming this
### is not part of the MADlib source code, then the following two commands
### may have to be used:
# git clone https://github.com/apache/incubator-madlib.git
# pushd incubator-madlib
#####################################################################################

docker build -t madlib -f tool/docker/postgres/Dockerfile_9_6 .
### Steps to use the image for installing MADlib.
docker run -d --name madlib madlib
## This sleep is required since it takes a couple of seconds for the docker
## container to come up, which is required by the docker exec command that follows.
sleep 5
docker exec -it madlib /incubator-madlib/build/src/bin/madpack -p postgres -c postgres/postgres@localhost:5432/postgres install
docker exec -it madlib /incubator-madlib/build/src/bin/madpack -p postgres  -c postgres/postgres@localhost:5432/postgres install-check

docker kill madlib
docker rm madlib
