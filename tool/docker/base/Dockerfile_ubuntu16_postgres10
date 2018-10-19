#
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

FROM ubuntu:16.04

### Get necessary libraries to add postgresql apt repository
RUN apt-get update && apt-get install -y lsb-core software-properties-common wget

### Add postgresql apt repository
RUN add-apt-repository "deb http://apt.postgresql.org/pub/repos/apt/ $(lsb_release -sc)-pgdg main" && wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - 

### Have to update after getting new repository
RUN apt-get update

### Get postgres10 and postgres specific add-ons
RUN apt-get install -y postgresql-10 \
                       postgresql-client-10 \
                       postgresql-plpython-10 \ 
                       postgresql-server-dev-10 \
                       libpq-dev \
                       build-essential \
                       openssl \
                       libssl-dev \
                       libboost-all-dev \
                       m4 \
                       vim \
                       pgxnclient \
                       flex \
                       bison \
                       graphviz

### Reset pg_hba.conf file to allow no password prompt
### Docker file doesn't support heardoc, like cat > /etc/postgresql/10/main/pg_hba.conf<<-EOF,
### and this echo and \n\ are workaround to write the file
RUN echo " \n\
    # Database administrative login by Unix domain socket \n\
    local   all             all                                     trust \n\

    # TYPE  DATABASE        USER            ADDRESS                 METHOD \n\

    # "local" is for Unix domain socket connections only \n\
    local   all             all                                     trust \n\
    # IPv4 local connections: \n\
    host    all             all             127.0.0.1/32            trust \n\
    # IPv6 local connections: \n\
    host    all             all             ::1/128                 trust \n\
" > /etc/postgresql/10/main/pg_hba.conf

### We need to set nproc to unlimited to be able to run scripts as
### the user 'postgres'. This is actually useful when we try to setup
### and start a Postgres server.
RUN echo " * soft nproc unlimited " > /etc/security/limits.d/postgres-limits.conf


### Always start postgres server when login
RUN echo "service postgresql start" >> ~/.bashrc

### Build custom CMake with SSQL support
RUN wget https://cmake.org/files/v3.6/cmake-3.6.1.tar.gz && \
      tar -zxvf cmake-3.6.1.tar.gz && \
      cd cmake-3.6.1 && \
      sed -i 's/-DCMAKE_BOOTSTRAP=1/-DCMAKE_BOOTSTRAP=1 -DCMAKE_USE_OPENSSL=ON/g' bootstrap && \
      ./configure &&  \
      make -j2 && \
      make install && \
      cd ..

### Install doxygen-1.8.13:
RUN wget http://ftp.stack.nl/pub/users/dimitri/doxygen-1.8.13.src.tar.gz && \
      tar xf doxygen-1.8.13.src.tar.gz && \
      cd doxygen-1.8.13 && \
      mkdir build && \
      cd build && \
      cmake -G "Unix Makefiles" .. && \
      make && \
      make install

### Optional: install LaTex
### uncomment the following 'RUN apt-get' line to bake LaTex into the image
### Note: if you run the following line, please tag the image as
### madlib/postgres_10:LaTex, and don't tag it as latest
# RUN apt-get install -y texlive-full

## To build an image from this docker file without LaTex, from madlib folder, run:
## docker build -t madlib/postgres_10:latest -f tool/docker/base/Dockerfile_ubuntu16_postgres10 .
## To push it to docker hub, run:
## docker push madlib/postgres_10:latest

## To build an image from this docker file with LaTex, from madlib folder, uncomment
## line 88, and run:
## docker build -t madlib/postgres_10:LaTex -f tool/docker/base/Dockerfile_ubuntu16_postgres10 .
## To push it to docker hub, run:
## docker push madlib/postgres_10:LaTex
