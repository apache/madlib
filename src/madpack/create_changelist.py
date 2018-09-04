#!/usr/bin/python
# ------------------------------------------------------------------------------
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
# ------------------------------------------------------------------------------

# Create changelist for any two branches

# Prequisites:
# The old version has to be installed in the "madlib_old_vers" schema
# The new version has to be installed in the "madlib" (default) schema
# Two branches must exist locally (run 'git fetch' to ensure you have the latest version)

# Usage:
# python create_changelist.py <changelist filename> <old version branch> <new version branch>

# Example (should be equivalent to changelist_1.13_1.14.yaml):
# python create_changelist.py chtest1.yaml rel/v1.13 rel/v1.14

import sys
import os

ch_filename = sys.argv[1]
old_vers = sys.argv[2]
new_vers = sys.argv[3]

if os.path.exists(ch_filename):
    print "{0} already exists".format(ch_filename)
    raise SystemExit
print "Creating changelist {0}".format(ch_filename)
os.system("rm -f /tmp/madlib_tmp_nm.txt /tmp/madlib_tmp_udf.txt /tmp/madlib_tmp_udt.txt")
f = open(ch_filename, "w")
f.write(
"""# ------------------------------------------------------------------------------
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
# ------------------------------------------------------------------------------
""")

f.write(
"""
# Changelist for MADlib version {old_vers} to {new_vers}

# This file contains all changes that were introduced in a new version of
# MADlib. This changelist is used by the upgrade script to detect what objects
# should be upgraded (while retaining all other objects from the previous version)

# New modules (actually .sql_in files) added in upgrade version
# For these files the sql_in code is retained as is with the functions in the
# file installed on the upgrade version. All other files (that don't have
# updates), are cleaned up to remove object replacements
""".format(**locals()))

os.system("git diff {old_vers} {new_vers} --name-only --diff-filter=A > /tmp/madlib_tmp_nm.txt".format(**locals()))

f.write("new module:\n")
with open('/tmp/madlib_tmp_nm.txt') as fp:
    for line in fp:
        if 'sql_in' in line and '/test/' not in line:
             f.write('    ' + line.split('/')[5].split('.')[0]+':\n')

os.system("psql madlib -f diff_udf.sql > /tmp/madlib_tmp_udf.txt")
os.system("psql madlib -f diff_udt.sql > /tmp/madlib_tmp_udt.txt")

f.write("\n# Changes in the types (UDT) including removal and modification\n")
f.write("udt:\n")
with open('/tmp/madlib_tmp_udt.txt') as fp:
    for line in fp:
       if 'UDT' in line:
            f.write('    ' + line.split('|')[1].strip()+":\n")

f.write(
"""
# List of the UDF changes that affect the user externally. This includes change
# in function name, return type, argument order or types, or removal of
# the function. In each case, the original function is as good as removed and a
# new function is created. In such cases, we should abort the upgrade if there
# are user views dependent on this function, since the original function will
# not be present in the upgraded version.
""")
f.write("udf:\n")
with open('/tmp/madlib_tmp_udf.txt') as fp:
    for line in fp:
        if 'type' in line:
            if 'agg' in line:
                f.write("""
# Changes to aggregates (UDA) including removal and modification
# Overloaded functions should be mentioned separately
""")
                f.write("uda:\n")
        if 'UDF' in line:
            f.write(line.split('|')[1])


f.write(
"""
# List of the UDC, UDO and UDOC changes.
""")
#TODO: We need to decide how we want to check for these
f.write("udc:\n")
f.write("udo:\n")
f.write("udoc:\n")

os.system("rm -f /tmp/madlib_tmp_nm.txt /tmp/madlib_tmp_udf.txt /tmp/madlib_tmp_udt.txt")
