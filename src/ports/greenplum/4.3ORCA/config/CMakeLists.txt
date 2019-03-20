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

add_current_greenplum_version()

# -- 1. Copy all *.yml files ---------------------------------------------------

file(GLOB_RECURSE CONFIG_FILES
    RELATIVE "${CMAKE_CURRENT_SOURCE_DIR}"
    "*.yml"
)
add_files(CONFIG_TARGET_FILES . "${CMAKE_CURRENT_BINARY_DIR}" ${CONFIG_FILES})
add_custom_target(configFilesgp43 ALL DEPENDS ${CONFIG_TARGET_FILES})


# -- 2. Install config files to config ----------------------------

install(FILES ${CONFIG_TARGET_FILES}
    DESTINATION ports/greenplum/4.3ORCA/config
    COMPONENT core
)
