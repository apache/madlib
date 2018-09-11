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

# Create changelist for any two branches/tags

# Prequisites:
# The old version has to be installed in the "madlib_old_vers" schema
# The new version has to be installed in the "madlib" (default) schema
# Two branches/tags must exist locally (run 'git fetch' to ensure you have the latest version)

# Usage (must be executed in the src/madpack directory):
# python create_changelist.py <changelist filename> <old version branch> <new version branch>

# Example (should be equivalent to changelist_1.13_1.14.yaml):
# python create_changelist.py chtest1.yaml rel/v1.13 rel/v1.14

import sys
import os

ch_filename = sys.argv[1]
old_vers = sys.argv[2]
new_vers = sys.argv[3]
database = sys.argv[4]

if os.path.exists(ch_filename):
    print "{0} already exists".format(ch_filename)
    raise SystemExit

err1 = os.system("""psql {0} -l > /dev/null""".format(database))
if err1 != 0:
    print "Database {0} does not exist".format(old_vers)
    raise SystemExit

err1 = os.system("""psql {0} -c "select madlib_old_vers.version()" > /dev/null
                 """.format(database))
if err1 != 0:
    print "Schema {0} does not exist".format(old_vers)
    raise SystemExit

err1 = os.system("""psql {0} -c "select madlib.version()" > /dev/null
                 """.format(database))
if err1 != 0:
    print "Schema {0} does not exist".format(new_vers)
    raise SystemExit

print "Creating changelist {0}".format(ch_filename)
os.system("rm -f /tmp/madlib_tmp_nm.txt /tmp/madlib_tmp_udf.txt /tmp/madlib_tmp_udt.txt")
try:
    f = open("/tmp/madlib_tmp_cl.yaml", "w")
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

    # Find the new modules using the git diff
    os.system("git diff {old_vers} {new_vers} --name-only --diff-filter=A > /tmp/madlib_tmp_nm.txt".format(**locals()))

    f.write("new module:\n")
    with open('/tmp/madlib_tmp_nm.txt') as fp:
        for line in fp:
            if 'sql_in' in line and '/test/' not in line:
                 f.write('    ' + line.split('/')[5].split('.')[0]+':\n')

    # Find the changed types and keep a list for future use
    os.system("psql {0} -f diff_udt.sql > /tmp/madlib_tmp_udt.txt".format(database))

    f.write("\n# Changes in the types (UDT) including removal and modification\n")
    f.write("udt:\n")
    udt_list=[]
    with open('/tmp/madlib_tmp_udt.txt') as fp:
        for line in fp:
           if 'UDT' in line and '[]' not in line:
                ch_type = line.split('|')[1].strip()
                udt_list.append(ch_type)
                f.write('    ' + ch_type +":\n")

    # Find the list of UDFs and UDAs
    # There are two main sources for these lists.
    # 1. The functions that actually got changed
    # 2. The functions that depend on a changed type

    # We will keep two lists (for UDF and UDA) and fill them as we parse the
    # output of diff functions

    udf_list=[]
    uda_list=[]
    current_list = udf_list

    os.system("psql {0} -f diff_udf.sql > /tmp/madlib_tmp_udf.txt".format(database))

    with open('/tmp/madlib_tmp_udf.txt') as fp:
        for line in fp:
            if 'type' in line:
                if 'agg' in line:
                    current_list = uda_list

            if 'UDF' in line:
                current_list.append('    ' + line.split('|')[1].strip()+"\n")
                #f.write('    ' + line.split('|')[1].strip()+"\n")

    current_list = udf_list

    # Find the function that depend on changed types
    if os.path.exists("/tmp/madlib_tmp_typedep.txt"):
        os.system("rm /tmp/madlib_tmp_typedep.txt")
    os.system("touch /tmp/madlib_tmp_typedep.txt")
    for t in udt_list:
        print "type {0}".format(t)
        call = """psql {database} -c "DROP TABLE IF EXISTS __tmp__madlib__ " """.format(**locals())
        print call
        os.system(call)
        call = """psql {database} -c "SELECT get_functions('__tmp__madlib__', 'madlib_old_vers', 'madlib_old_vers.{t}')" """.format(**locals())
        print call
        os.system(call)
        print "here"
        call = """psql {database} -x -c "SELECT type, name, retype, argtypes FROM __tmp__madlib__ ORDER BY type DESC" > /tmp/madlib_tmp_typedep.txt """.format(**locals())
        print call
        os.system(call)

        with open('/tmp/madlib_tmp_typedep.txt') as fp:
            for line in fp:
                # print line
                if '|' in line:
                    sp = line.split('|')
                    # print sp

                    # Type is only used for normal/agg switch
                    if sp[0].strip() == 'type':
                        if sp[1].strip() == 'agg':
                            current_list = uda_list

                    # Add the functions with formatting
                    elif sp[0].strip() == 'name':
                        current_list.append('    - ' + sp[1].strip() + ":\n")
                    elif sp[0].strip() == 'retype':
                        current_list.append('        rettype: ' + sp[1].strip() + "\n")
                    elif sp[0].strip() == 'argtypes':
                        current_list.append('        argument: ' + sp[1].strip() + "\n")

    print udf_list
    print uda_list

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

    for line in udf_list:
        f.write(line)

    f.write("""
# Changes to aggregates (UDA) including removal and modification
# Overloaded functions should be mentioned separately
""")
    f.write("uda:\n")

    for line in uda_list:
        f.write(line)

    #TODO: We need to decide how we want to check for these
    f.write(
    """
# List of the UDC, UDO and UDOC changes.
""")
    f.write("udc:\n")
    f.write("udo:\n")
    f.write("udoc:\n")
    f.close()
    os.system("cp /tmp/madlib_tmp_cl.yaml {0}".format(ch_filename))
except:
    print "Something went wrong! The changelist might be wrong/corrupted."
    raise
finally:
    os.system("rm -f /tmp/madlib_tmp_nm.txt /tmp/madlib_tmp_udf.txt "
              "/tmp/madlib_tmp_udt.txt /tmp/madlib_tmp_cl.yaml")
