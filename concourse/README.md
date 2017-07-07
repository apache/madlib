<!-- Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.  The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License. -->

## Concourse pipeline configuration and scripts

This directory contains pipelines, task files, and scripts to run various sets of builds and tests on [our Concourse continuous integration server](http://gpdb.ci.pivotalci.info/).

This work is dependent on [GPDB concourse scripts](https://github.com/greenplum-db/gpdb/tree/master/concourse).

[Learn more about Concourse overall](http://concourse.ci/)

### Prerequisites

- An S3 bucket for your pipeline to use
- GPDB installation (unless you want to compile from source)
- fly CLI

### How to create a pipeline:

- Log in to https://gpdb.ci.pivotalci.info/ gpdb team
- Download and install fly CLI from the links on the lower right corner
- Create a yml file to replace the various variables from the pipeline
- Use fly set-pipeline command

### Examples

Create a pipeline for MADlib stable running on GPDB master:

fly -t gpdb set-pipeline -p dev:madlib_**MYID** -c ./incubator-madlib/concourse/pipelines/madlib_pipeline.yml -l path-to-secrets/madlib-ci-secrets.yml -l path-to-secrets/gpdb_master-ci-secrets.yml

Create a pipeline for MADlib master running on GPDB stable:

fly -t gpdb set-pipeline -p dev:madlib_master_**MYID** -c ./incubator-madlib/concourse/pipelines/madlib_master_pipeline.yml -l path-to-secrets/madlib-ci-secrets.yml -l path-to-secrets/gpdb-release-secrets.dev.yml


