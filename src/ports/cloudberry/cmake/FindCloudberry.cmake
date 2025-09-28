# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at

#   http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

# Set defaults that can be overridden by files that include this file:
if(NOT DEFINED _FIND_PACKAGE_FILE)
    set(_FIND_PACKAGE_FILE "${CMAKE_CURRENT_LIST_FILE}")
endif(NOT DEFINED _FIND_PACKAGE_FILE)

# Set parameters for calling FindPostgreSQL.cmake
set(_NEEDED_PG_CONFIG_PACKAGE_NAME "Apache Cloudberry")
set(_PG_CONFIG_VERSION_NUM_MACRO "GP_VERSION_NUM")
set(_PG_CONFIG_VERSION_MACRO "GP_VERSION")
set(_SEARCH_PATH_HINTS
    "/usr/local/cloudberry-db-devel/bin"
    "/usr/local/cloudberry-db/bin"
    "/usr/local/cloudberry/bin"
    "$ENV{GPHOME}/bin"
)

include("${CMAKE_CURRENT_LIST_DIR}/../../postgres/cmake/FindPostgreSQL.cmake")

if(${PKG_NAME}_FOUND)
    # server/funcapi.h ultimately includes server/access/xact.h, from which
    # cdb/cdbpathlocus.h is included
    execute_process(COMMAND ${${PKG_NAME}_PG_CONFIG} --pkgincludedir
        OUTPUT_VARIABLE ${PKG_NAME}_ADDITIONAL_INCLUDE_DIRS
        OUTPUT_STRIP_TRAILING_WHITESPACE
    )
    set(${PKG_NAME}_ADDITIONAL_INCLUDE_DIRS
        "${${PKG_NAME}_ADDITIONAL_INCLUDE_DIRS}/internal")
    message("-- Detected Cloudberry")
endif(${PKG_NAME}_FOUND)
