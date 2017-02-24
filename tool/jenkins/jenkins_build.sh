#!/bin/sh

#####################################################################################
### If this bash script is executed as a stand-alone file, assuming this
### is not part of the MADlib source code, then the following two commands
### may have to be used:
# git clone https://github.com/apache/incubator-madlib.git
# pushd incubator-madlib
#####################################################################################

# Pull down the base docker images
docker pull madlib/postgres_9_6:jenkins
# Assuming git clone of incubator-madlib has been done, launch a container with the volume mounted
docker run -d --name madlib -v incubator-madlib:/incubator-madlib madlib/postgres_9.6:jenkins
## This sleep is required since it takes a couple of seconds for the docker
## container to come up, which is required by the docker exec command that follows.
sleep 5
# cmake, make and make install MADlib
docker exec madlib bash -c 'mkdir /incubator-madlib/build ; cd /incubator-madlib/build ; cmake .. ; make ; make install'
# Install MADlib and run install check
docker exec -it madlib /incubator-madlib/build/src/bin/madpack -p postgres -c postgres/postgres@localhost:5432/postgres install
docker exec -it madlib /incubator-madlib/build/src/bin/madpack -p postgres  -c postgres/postgres@localhost:5432/postgres install-check

docker kill madlib
docker rm madlib
