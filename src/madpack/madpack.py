#!/usr/bin/env python3
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# Main Madpack installation executable.
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
import sys
import getpass
import re
import os
import glob
import traceback
import subprocess
import datetime
import tempfile
import shutil

import upgrade_util as uu
from utilities import _write_to_file
from utilities import error_
from utilities import get_dbver
from utilities import get_db_madlib_version
from utilities import get_rev_num
from utilities import info_
from utilities import is_rev_gte
from utilities import remove_comments_from_sql
from utilities import run_query

# Required Python version
py_min_ver = [2, 7]

if list(sys.version_info[:2]) < py_min_ver:
    print("ERROR: python version too old ({0}). You need {1} or greater.".
          format('.'.join(map(str, sys.version_info[:3])),
                 '.'.join(map(str, py_min_ver))))
    exit(1)

# raw_input isn't defined in Python3.x, whereas input wasn't behaving like raw_input in Python 2.x
# this should make both input and raw_input work in Python 2.x/3.x like the raw_input from Python 2.x
try: input = raw_input
except NameError: raw_input = input

# Find MADlib root directory. This file is installed to
# $MADLIB_ROOT/madpack/madpack.py, so to get $MADLIB_ROOT we need to go
# two levels up in the directory hierarchy. We use (a) os.path.realpath and
# (b) __file__ (instead of sys.argv[0]) because madpack.py could be called
# (a) through a symbolic link and (b) not as the main module.
maddir = os.path.abspath(os.path.dirname(os.path.realpath(__file__)) + "/..")   # MADlib root dir
sys.path.append(maddir + "/madpack")

# Import MADlib python modules
import argparse
import configyml

# Some read-only variables
this = os.path.basename(sys.argv[0])    # name of this script

# Default directories
maddir_conf = maddir + "/config"           # Config dir
maddir_lib = "libmadlib.so"  # C/C++ libraries

# Read the config files
ports = configyml.get_ports(maddir_conf)  # object made of Ports.yml
new_madlib_ver = configyml.get_version(maddir_conf)  # MADlib OS-level version
portid_list = []
for port in ports:
    portid_list.append(port)

SUPPORTED_PORTS = ('postgres', 'greenplum')

# Global variables
portid = None       # Target port ID (eg: pg90, gp40)
dbver = None        # DB version
con_args = {}       # DB connection arguments
verbose = None      # Verbose flag
keeplogs = None
tmpdir = None

DB_CREATE_OBJECTS = "db_create_objects"
INSTALL_DEV_CHECK = "install_dev_check"
UNIT_TEST = "unit_test"

def _make_dir(dir):
    """
    # Create a temp dir
    # @param dir temp directory path
    """
    if not os.path.isdir(dir):
        try:
            os.makedirs(dir)
        except:
            print("ERROR: can not create directory: %s. Check permissions." % dir)
            exit(1)
# ------------------------------------------------------------------------------


def _internal_run_query(sql, show_error):
    """
    Runs a SQL query on the target platform DB
    using the default command-line utility.
    Very limited:
      - no text output with "new line" characters allowed
         @param sql query text to execute
         @param show_error displays the SQL error msg
    """
    return run_query(sql, con_args, show_error)
# ------------------------------------------------------------------------------

def _get_relative_maddir(maddir, port):
    """ Return a relative path version of maddir

    GPDB installations have a symlink outside of GPHOME that
    links to the current GPHOME. After a DB upgrade, this symlink is updated to
    the new GPHOME.

    'maddir_lib', which uses the absolute path of GPHOME, is hardcoded into each
    madlib function definition. Replacing the GPHOME path with the equivalent
    relative path makes it simpler to perform DB upgrades without breaking MADlib.
    """
    if port == 'postgres':
        # do nothing for postgres
        return maddir

    # e.g. maddir_lib = $GPHOME/madlib/Versions/1.9/lib/libmadlib.so
    # 'madlib' is supposed to be in this path, which is the default folder
    # used by GPPKG to install madlib
    try:
        abs_gphome, tail = maddir.split('madlib/')
    except ValueError:
        return maddir

    # Check outside $GPHOME if there is a symlink to this absolute path
    # os.pardir is equivalent to ..
    # os.path.normpath removes the extraneous .. from that path
    rel_gphome = os.path.normpath(os.path.join(abs_gphome, os.pardir, 'greenplum-db'))
    if (os.path.islink(rel_gphome) and
            os.path.realpath(rel_gphome) == os.path.realpath(abs_gphome)):
        # if the relative link exists and is pointing to current location
        return os.path.join(rel_gphome, 'madlib', tail)
    else:
        return maddir
# ------------------------------------------------------------------------------

def _cleanup_comments_in_sqlfile(output_filename, upgrade):
    """
    @brief Remove comments in the sql script, and re-write the file with the
    cleaned up script.
    """
    if not upgrade:
        with open(output_filename, 'r+') as output_filehandle:
            full_sql = output_filehandle.read()
            full_sql = remove_comments_from_sql(full_sql)
        # Re-write the cleaned-up sql to a new file. Python does not let us
        # erase all the content of a file and rewrite the same file again.
        cleaned_output_filename = output_filename+'.tmp'
        with open(cleaned_output_filename, 'w') as output_filehandle:
            _write_to_file(output_filehandle, full_sql)
        # Move the cleaned output file to the old one.
        os.rename(cleaned_output_filename, output_filename)

def _run_m4_and_append(schema, maddir_mod_py, module, sqlfile,
                       output_filehandle, pre_sql=None):
    """
    Function to process a sql file with M4.
    """
    # Check if the SQL file exists
    if not os.path.isfile(sqlfile):
        error_(this, "Missing module SQL file (%s)" % sqlfile, False)
        raise ValueError

    # Prepare the file using M4
    try:
        # Add the before SQL
        if pre_sql:
            output_filehandle.writelines([pre_sql, '\n\n'])
        # Find the madpack dir (platform specific or generic)
        if os.path.isdir(maddir + "/ports/" + portid + "/" + dbver + "/madpack"):
            maddir_madpack = maddir + "/ports/" + portid + "/" + dbver + "/madpack"
        else:
            maddir_madpack = maddir + "/madpack"
        maddir_ext_py = maddir + "/lib/python"

        m4args = ['m4',
                  '-P',
                  '-DMADLIB_SCHEMA=' + schema,
                  '-DPLPYTHON_LIBDIR=' + maddir_mod_py,
                  '-DEXT_PYTHON_LIBDIR=' + maddir_ext_py,
                  '-DMODULE_PATHNAME=' + maddir_lib,
                  '-DMADLIB_LIBRARY_PATH=' + madlib_library_path,
                  '-DMODULE_NAME=' + module,
                  '-I' + maddir_madpack,
                  sqlfile]
        if ( (portid == 'postgres') &
             (is_rev_gte(get_rev_num(dbver), get_rev_num('14.0'))) ):
            m4args = ['m4',
                  '-P',
                  '-DMADLIB_SCHEMA=' + schema,
                  '-DPLPYTHON_LIBDIR=' + maddir_mod_py,
                  '-DEXT_PYTHON_LIBDIR=' + maddir_ext_py,
                  '-DMODULE_PATHNAME=' + maddir_lib,
                  '-DMADLIB_LIBRARY_PATH=' + madlib_library_path,
                  '-DMODULE_NAME=' + module,
                  '-DUSE_COMPATIBLE_ARRAY=TRUE',
                  '-I' + maddir_madpack,
                  sqlfile]

        info_(this, "> ... parsing: " + " ".join(m4args), verbose)
        output_filehandle.flush()
        subprocess.call(m4args, stdout=output_filehandle)
    except:
        error_(this, "Failed executing m4 on %s" % sqlfile, False)
        raise Exception

def _run_install_check_sql(schema, maddir_mod_py, module, sqlfile,
                           tmpfile, logfile, pre_sql):
    """
        Run SQL file
            @param schema name of the target schema
            @param maddir_mod_py name of the module dir with Python code
            @param module  name of the module
            @param sqlfile name of the file to parse
            @param tmpfile name of the temp file to run
            @param logfile name of the log file (stdout)
            @param pre_sql optional SQL to run before executing the file
    """
    try:
        f = open(tmpfile, 'w')
        _run_m4_and_append(schema, maddir_mod_py, module, sqlfile, f, pre_sql)
        f.close()
    except:
        error_(this, "Failed to temp m4 processed file %s." % tmpfile, False)
        raise Exception
    # Only update function definition
    sub_module = ''
    # Run the SQL using DB command-line utility
    if portid in SUPPORTED_PORTS:
        sqlcmd = 'psql'
        # Test the DB cmd line utility
        std, err = subprocess.Popen(['which', sqlcmd], stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE).communicate()
        if not std:
            error_(this, "Command not found: %s" % sqlcmd, True)

        runcmd = [sqlcmd, '-a',
                  '-v', 'ON_ERROR_STOP=1',
                  '-h', con_args['host'].split(':')[0],
                  '-p', con_args['host'].split(':')[1],
                  '-d', con_args['database'],
                  '-U', con_args['user'],
                  '--no-password',
                  '-f', tmpfile]
        runenv = os.environ
        if 'password' in con_args:
            runenv["PGPASSWORD"] = con_args['password']
        runenv["PGOPTIONS"] = '-c client_min_messages=notice'

    # Open log file
    try:
        log = open(logfile, 'w')
    except:
        error_(this, "Cannot create log file: %s" % logfile, False)
        raise Exception

    # Run the SQL
    try:
        info_(this, "> ... executing " + tmpfile, verbose)
        retval = subprocess.call(runcmd, env=runenv, stdout=log, stderr=log)
    except:
        error_(this, "Failed executing %s" % tmpfile, False)
        raise Exception
    finally:
        log.close()

    return retval
# ------------------------------------------------------------------------------

def _run_sql_file(schema, sqlfile):
    """
        Run SQL file
            @param schema name of the target schema
            @param sqlfile name of the file to parse
    """
    # Run the SQL using DB command-line utility
    if portid in SUPPORTED_PORTS:
        sqlcmd = 'psql'
        # Test the DB cmd line utility
        std, err = subprocess.Popen(['which', sqlcmd], stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE).communicate()
        if not std:
            error_(this, "Command not found: %s" % sqlcmd, True)

        runcmd = [sqlcmd, '-a',
                  '-v', 'ON_ERROR_STOP=1',
                  '-h', con_args['host'].split(':')[0],
                  '-p', con_args['host'].split(':')[1],
                  '-d', con_args['database'],
                  '-U', con_args['user'],
                  '--no-password',
                  '--single-transaction',
                  '-f', sqlfile]
        runenv = os.environ
        if 'password' in con_args:
            runenv["PGPASSWORD"] = con_args['password']
        runenv["PGOPTIONS"] = '-c client_min_messages=notice'

    # Open log file
    logfile = sqlfile + '.log'
    try:
        log = open(logfile, 'w')
    except:
        error_(this, "Cannot create log file: %s" % logfile, False)
        raise Exception

    # Run the SQL
    try:
        info_(this, "> ... executing " + sqlfile, verbose)
        info_(this, ' '.join(runcmd), verbose)
        retval = subprocess.call(runcmd, env=runenv, stdout=log, stderr=log)
    except:
        error_(this, "Failed executing %s" % sqlfile, False)
        raise Exception
    finally:
        log.close()
    # Check the exit status
    result = _parse_result_logfile(retval, logfile, sqlfile)
    return result
# ------------------------------------------------------------------------------

def _parse_result_logfile(retval, logfile, sql_abspath,
                          sql_filename=None, module=None, milliseconds=None):
    """
    Function to parse the logfile and return if its content indicate a failure
    or success.
    """
    is_install_check_logfile = bool(sql_filename and module)
    # Check the exit status
    if retval != 0:
        result = 'FAIL'
        global keeplogs
        keeplogs = True
    # Since every single statement in the test file gets logged,
    # an empty log file indicates an empty or a failed test
    elif os.path.isfile(logfile) and os.path.getsize(logfile) > 0:
        result = 'PASS'
    # Otherwise
    else:
        result = 'ERROR'

    if is_install_check_logfile:
        # Output result
        print("TEST CASE RESULT|Module: " + module + \
            "|" + os.path.basename(sql_filename) + "|" + result + \
            "|Time: %d milliseconds" % (milliseconds))

    if result == 'FAIL':
        error_(this, "Failed executing %s" % sql_abspath, stop=False)
        error_(this, "Check the log at %s" % logfile, stop=False)
    return result


def _check_db_port(portid):
    """
    Make sure we are connected to the expected DB platform
        @param portid expected DB port id - to be validates
    """
    # Postgres
    try:
        row = _internal_run_query("SELECT version() AS version", True)
    except:
        error_(this, "Cannot validate DB platform type", True)
    if row and row[0]['version'].lower().find(portid) >= 0:
        if portid == 'postgres':
            if row[0]['version'].lower().find('greenplum') < 0:
                return True
        elif portid == 'greenplum':
            return True
    return False
# ------------------------------------------------------------------------------


def _print_vers(new_madlib_ver, db_madlib_ver, con_args, schema):
    """
    Print version information
        @param new_madlib_ver OS-level MADlib version
        @param db_madlib_ver DB-level MADlib version
        @param con_args database connection arguments
        @param schema MADlib schema name
    """
    info_(this, "MADlib tools version    = %s (%s)" % (str(new_madlib_ver), sys.argv[0]), True)
    if con_args:
        try:
            info_(this, "MADlib database version = %s (host=%s, db=%s, schema=%s)"
                  % (db_madlib_ver, con_args['host'], con_args['database'], schema), True)
        except:
            info_(this, "MADlib database version = [Unknown] (host=%s, db=%s, schema=%s)"
                  % (db_madlib_ver, con_args['host'], con_args['database'], schema), True)
    return
# ------------------------------------------------------------------------------


def _plpy_check(py_min_ver):
    """
    Check pl/python existence and version
        @param py_min_ver min Python version to run MADlib
    """

    info_(this, "Testing PL/Python environment...", True)

    # Check PL/Python existence
    rv = _internal_run_query("SELECT count(*) AS CNT FROM pg_language "
                             "WHERE lanname = 'plpython3u'", True)
    if int(rv[0]['cnt']) > 0:
        info_(this, "> PL/Python already installed", verbose)
    else:
        info_(this, "> PL/Python not installed", verbose)
        info_(this, "> Creating language PL/Python...", True)
        try:
            _internal_run_query("CREATE LANGUAGE plpython3u;", True)
        except:
            error_(this, """Cannot create language plpython3u. Please check if you
                have configured and installed portid (your platform) with
                `--with-python` option. Stopping installation...""", False)
            raise Exception

    # Check PL/Python version
    _internal_run_query("DROP FUNCTION IF EXISTS plpy_version_for_madlib();", False)
    _internal_run_query("""
        CREATE OR REPLACE FUNCTION plpy_version_for_madlib()
        RETURNS TEXT AS
        $$
            import sys
            # return '.'.join(str(item) for item in sys.version_info[:3])
            return str(sys.version_info[:3]).replace(',','.').replace(' ','').replace(')','').replace('(','')
        $$
        LANGUAGE plpython3u;
    """, True)
    rv = _internal_run_query("SELECT plpy_version_for_madlib() AS ver;", True)
    python = rv[0]['ver']
    py_cur_ver = [int(i) for i in python.split('.')]
    if py_cur_ver >= py_min_ver:
        info_(this, "> PL/Python version: %s" % python, verbose)
    else:
        error_(this, "PL/Python version too old: %s. You need %s or greater"
               % (python, '.'.join(str(i) for i in py_min_ver)), False)
        raise Exception
    _internal_run_query("DROP FUNCTION IF EXISTS plpy_version_for_madlib();", False)
    info_(this, "> PL/Python environment OK (version: %s)" % python, True)
# ------------------------------------------------------------------------------


def _db_install(schema, is_schema_in_db, filehandle):
    """
    Install MADlib
        @param schema MADlib schema name
        @param is_schema_in_db flag to indicate if schema is already present
        @param filehandle file that contains the sql for installation
        @param testcase command-line args for a subset of modules
    """
    # Create MADlib objects
    try:
        _db_create_schema(schema, is_schema_in_db, filehandle)
        _db_create_objects(schema, filehandle)
    except:
        error_(this, "Building database objects failed. "
               "Before retrying: drop %s schema OR install MADlib into "
               "a different schema." % schema, True)

# ------------------------------------------------------------------------------


def _db_upgrade(schema, filehandle, db_madlib_ver):
    """
    Upgrade MADlib
        @param schema MADlib schema name
        @param filehandle Handle to output file
        @param db_madlib_ver DB-level MADlib version
    """
    if is_rev_gte(get_rev_num(db_madlib_ver), get_rev_num(new_madlib_ver)):
        info_(this, "Current MADlib version already up to date.", True)
        return 1

    if is_rev_gte(get_rev_num('1.9.1'), get_rev_num(db_madlib_ver)):
        error_(this, """
            MADlib versions prior to v1.10 are not supported for upgrade.
            Please try upgrading to v1.10 and then upgrade to this version.
            """, True)
        return 1

    info_(this, "Upgrading MADlib into %s schema..." % schema, True)
    info_(this, "\tDetecting dependencies...", True)

    info_(this, "\tLoading change list...", True)
    ch = uu.ChangeHandler(schema, portid, con_args, maddir, db_madlib_ver, filehandle)

    info_(this, "\tDetecting table dependencies...", True)
    td = uu.TableDependency(schema, portid, con_args)

    info_(this, "\tDetecting view dependencies...", True)
    vd = uu.ViewDependency(schema, portid, con_args)

    abort = False
    if td.has_dependency():
        info_(this, "*" * 50, True)
        info_(this, "\tFollowing user tables/indexes are dependent on MADlib objects:", True)
        info_(this, td.get_dependency_str(), True)
        info_(this, "*" * 50, True)
        cd_udt = [udt for udt in td.get_depended_udt() if udt in ch.udt]
        if len(cd_udt) > 0:
            error_(this, """
                User has objects dependent on following updated MADlib types!
                        {0}
                These objects need to be dropped before upgrading.
                """.format('\n\t\t\t'.join(cd_udt)), False)

            # we add special handling for 'linregr_result'
            if 'linregr_result' in cd_udt:
                info_(this, """Dependency on 'linregr_result' could be due to objects
                        created from the output of the aggregate 'linregr'.
                        Please refer to the Linear Regression documentation
                        <http://madlib.apache.org/docs/latest/group__grp__linreg.html#warning>
                        for the recommended solution.
                        """, False)
            abort = True

        c_udoc = ch.get_udoc_oids()
        d_udoc = td.get_depended_udoc_oids()
        cd_udoc = [udoc for udoc in d_udoc if udoc in c_udoc]
        if len(cd_udoc) > 0:
            error_(this, """
                User has objects dependent on the following updated MADlib operator classes!
                        oid={0}
                These objects need to be dropped before upgrading.
                """.format('\n\t\t\t'.join(cd_udoc)), False)
            abort = True

    if vd.has_dependency():
        info_(this, "*" * 50, True)
        info_(this, "\tFollowing user views are dependent on MADlib objects:", True)
        info_(this, vd.get_dependency_graph_str(), True)
        info_(this, "*" * 50, True)

        d_udf = vd.get_depended_func_signature('UDF')
        if len(d_udf) > 0:
            error_(this, """
                User has objects dependent on following updated MADlib functions!
                    {0}
                These objects might fail to work with the updated functions and
                need to be dropped before starting upgrade again.
                """.format('\n\t\t\t\t\t'.join(d_udf)), False)
            abort = True

        d_uda = vd.get_depended_func_signature('UDA')
        if len(d_uda) > 0:
            error_(this, """
                User has objects dependent on following updated MADlib aggregates!
                    {0}
                These objects might fail to work with the new aggregates and
                need to be dropped before starting upgrade again.
                """.format('\n\t\t\t\t\t'.join(d_uda)), False)
            abort = True

        d_udo = vd.get_depended_opr_oids()
        if len(d_udo) > 0:
            error_(this, """
                User has objects dependent on following updated MADlib operators!
                    oid={0}
                These objects might fail to work with the new operators and
                need to be dropped before starting upgrade again.
                """.format('\n\t\t\t\t\t'.join(d_udo)), False)
            abort = True

    if abort:
        error_(this, """------- Upgrade aborted. -------
                Backup and drop all objects that depend on MADlib before trying upgrade again.
                Use madpack reinstall to automatically drop these objects only if appropriate.""", True)
    else:
        info_(this, "No dependency problem found, continuing to upgrade ...", True)

    info_(this, "\tReading existing UDAs/UDTs...", False)
    sc = uu.ScriptCleaner(schema, portid, con_args, ch)
    info_(this, "Script Cleaner initialized ...", False)

    function_drop_str = get_madlib_function_drop_str(schema)
    flist = function_drop_str.split("\n\n")
    for i in flist:
        _internal_run_query(i, True)

    operator_drop_str = get_madlib_operator_drop_str(schema)
    _internal_run_query(operator_drop_str, True)
    ch.drop_changed_udc()
    ch.drop_changed_udt()  # assume dependent udf for udt does not change
    _db_create_objects(schema, filehandle, True, sc)
    return 0
# ------------------------------------------------------------------------------


def _db_rename_schema(from_schema, to_schema):
    """
    Rename schema
        @param from_schema name of the schema to rename
        @param to_schema new name for the schema
    """

    info_(this, "> Renaming schema %s to %s" % (from_schema, to_schema), True)
    try:
        _internal_run_query("ALTER SCHEMA %s RENAME TO %s;" % (from_schema, to_schema), True)
    except:
        error_(this, 'Cannot rename schema. Stopping installation...', False)
        raise Exception
# ------------------------------------------------------------------------------


def _db_create_schema(schema, is_schema_in_db, filehandle):
    """
    Create schema
        @param from_schema name of the schema to rename
        @param is_schema_in_db flag to indicate if schema is already present
        @param to_schema new name for the schema
    """

    if not is_schema_in_db:
        _write_to_file(filehandle, "CREATE SCHEMA %s;" % schema)
# ------------------------------------------------------------------------------

def _process_py_sql_files_in_modules(modset, args_dict):
    """
        This function executes relevant files from all applicable modules
        (either all modules, or specific modules specified as a comma
        separated list).
        * If the operation is install/dev check, then all the corresponding sql
        files are executed.
        * If the operation is unit-test, then all corresponding python files
        are executed.
        * If the operation was from _db_create_objects(), then all the relevant
        objects are written to files for execution during install/reinstall/upgrade.
    """
    if 'madpack_cmd' in args_dict:
        madpack_cmd = args_dict['madpack_cmd']
    else:
        madpack_cmd = None

    if not madpack_cmd:
        calling_operation = DB_CREATE_OBJECTS
    elif madpack_cmd in ['install-check', 'dev-check']:
        calling_operation = INSTALL_DEV_CHECK
    elif madpack_cmd == 'unit-test':
        calling_operation = UNIT_TEST
    else:
        error_(this, "Invalid madpack operation: %s" % madpack_cmd, True)

    # Perform operations on all modules
    for moduleinfo in portspecs['modules']:
        # Get the module name
        module = moduleinfo['name']

        # Skip if doesn't meet specified modules
        if modset and module not in modset:
            continue

        # Find the Python module dir (platform specific or generic)
        if os.path.isdir(maddir + "/ports/" + portid + "/" + dbver + "/modules/" + module):
            maddir_mod_py = maddir + "/ports/" + portid + "/" + dbver + "/modules"
        else:
            maddir_mod_py = maddir + "/modules"

        # Find the SQL module dir (platform specific or generic)
        if os.path.isdir(maddir + "/ports/" + portid + "/modules/" + module):
            maddir_mod_sql = maddir + "/ports/" + portid + "/modules"
        elif os.path.isdir(maddir + "/modules/" + module):
            maddir_mod_sql = maddir + "/modules"
        else:
            # This was a platform-specific module, for which no default exists.
            # We can just skip this module.
            continue

        # Make a temp dir for log files
        cur_tmpdir = tmpdir + "/" + module
        _make_dir(cur_tmpdir)
        if calling_operation == DB_CREATE_OBJECTS:
            info_(this, "> - %s" % module, True)
            mask = maddir_mod_sql + '/' + module + '/*.sql_in'
        elif calling_operation == INSTALL_DEV_CHECK:
            if madpack_cmd == 'install-check':
                mask = maddir_mod_sql + '/' + module + '/test/*.ic.sql_in'
            else:
                mask = maddir_mod_sql + '/' + module + '/test/*.sql_in'
        elif calling_operation == UNIT_TEST:
            mask = maddir_mod_py + '/' + module + '/test/unit_tests/test_*.py'
        else:
            error_(this, "Something is wrong, shouldn't be here.", True)

        # Loop through all SQL files for this module
        source_files = glob.glob(mask)
        source_files = [s for s in source_files if '.setup' not in s]
        if calling_operation == INSTALL_DEV_CHECK and madpack_cmd != 'install-check':
            source_files = [s for s in source_files if '.ic' not in s]

        # Do this error check only when running install/reinstall/upgrade
        if calling_operation == DB_CREATE_OBJECTS and not source_files:
            error_(this, "No files found in: %s" % mask, True)

        # Execute all SQL/py files for the module
        for src_file in source_files:
            algoname = os.path.basename(src_file).split('.')[0]
            # run only algo specified
            if (modset and modset[module] and
                    algoname not in modset[module]):
                continue
            if calling_operation == DB_CREATE_OBJECTS:
                _execute_per_module_db_create_obj_algo(
                    args_dict['schema'],
                    maddir_mod_py,
                    module,
                    src_file,
                    algoname,
                    cur_tmpdir,
                    args_dict['upgrade'],
                    args_dict['create_obj_handle'],
                    args_dict['sc'])
            elif calling_operation == INSTALL_DEV_CHECK:
                # Skip certain tests for GP4.3
                if dbver == '4.3ORCA' and module in ['deep_learning', 'kmeans']:
                    continue
                _execute_per_module_install_dev_check_algo(
                    args_dict['schema'],
                    args_dict['test_user'],
                    maddir_mod_py,
                    module,
                    src_file,
                    cur_tmpdir)
            elif calling_operation == UNIT_TEST:
                _execute_per_module_unit_test_algo(
                    module,
                    src_file,
                    cur_tmpdir)
            else:
                error_(this, "Something is wrong, shouldn't be here: %s" % src_file, True)
        if calling_operation == DB_CREATE_OBJECTS:
            shutil.rmtree(cur_tmpdir)
# ------------------------------------------------------------------------------
def _execute_per_module_db_create_obj_algo(schema, maddir_mod_py, module,
                                           sqlfile, algoname, cur_tmpdir,
                                           upgrade, create_obj_handle, sc):
    """
        Perform operations that have to be done per module when
        _db_create_objects function is invoked
    """
    if not upgrade:
        _run_m4_and_append(schema, maddir_mod_py, module, sqlfile,
                           create_obj_handle, None)
    else:
        tmpfile = cur_tmpdir + '/' + os.path.basename(sqlfile) + '.tmp'
        with open(tmpfile, 'w+') as tmphandle:
            _run_m4_and_append(schema, maddir_mod_py, module, sqlfile,
                               tmphandle, None)
        processed_sql = sc.cleanup(open(tmpfile).read(), algoname)
        _write_to_file(create_obj_handle, processed_sql)

# ------------------------------------------------------------------------------
def _execute_per_module_unit_test_algo(module, pyfile, cur_tmpdir):
    """
        Perform opertions that have to be done per module when
        unit tests are run
    """
    logfile = cur_tmpdir + '/' + os.path.basename(pyfile) + '.log'
    try:
        log = open(logfile, 'w')
    except:
        error_(this, "Cannot create log file: %s" % logfile, False)
        raise Exception
    info_(this, "> ... executing " + pyfile, verbose)
    try:
        milliseconds = 0
        run_start = datetime.datetime.now()
        # Run the python unit test file
        runcmd = ["python3", pyfile]
        # runenv = os.environ
        runenv = os.environ.copy()

        # GPDB6 python3 support is provided by an additional package.
        # To access it, we will have to set environment variables.
        if dbver == '6':
            gphome = runenv["GPHOME"]
            runenv["LD_LIBRARY_PATH"] = "{0}/ext/python3.9/lib:".format(gphome) + runenv["LD_LIBRARY_PATH"]
            runenv["PATH"] = "{0}/ext/python3.9/bin:".format(gphome) + runenv["PATH"]
            runenv["PYTHONHOME"] = "{0}/ext/python3.9".format(gphome)
            runenv["PYTHONPATH"] = "{0}/ext/python3.9/lib".format(gphome)
        retval = subprocess.call(runcmd, env=runenv, stdout=log, stderr=log)
        run_end = datetime.datetime.now()
        milliseconds = round((run_end - run_start).seconds * 1000 +
                             (run_end - run_start).microseconds / 1000)
    except:
        error_(this, "Failed executing %s" % pyfile, False)
        raise Exception
    finally:
        log.close()
    _parse_result_logfile(retval, logfile, pyfile,
                          pyfile, module, milliseconds)

# ------------------------------------------------------------------------------
def _execute_per_module_install_dev_check_algo(schema, test_user,
                                               maddir_mod_py, module,
                                               sqlfile, cur_tmpdir):
    """
        Perform opertions that have to be done per module when
        install-check or dev-check is run
    """
    try:
        # Prepare test schema
        test_schema = "madlib_installcheck_%s" % (module)
        _internal_run_query("DROP SCHEMA IF EXISTS %s CASCADE; CREATE SCHEMA %s;" %
                            (test_schema, test_schema), True)
        _internal_run_query("GRANT ALL ON SCHEMA %s TO \"%s\";" %
                            (test_schema, test_user), True)

        # Switch to test user and prepare the search_path
        pre_sql = '-- Switch to test user:\n' \
                  'SET ROLE \"%s\";\n' \
                  '-- Set SEARCH_PATH for install-check:\n' \
                  'SET search_path=%s,%s;\n' \
                  % (test_user, test_schema, schema)


        # Set file names
        tmpfile = cur_tmpdir + '/' + os.path.basename(sqlfile) + '.tmp'
        logfile = cur_tmpdir + '/' + os.path.basename(sqlfile) + '.log'

        # If there is no problem with the SQL file
        milliseconds = 0

        # Run the SQL
        run_start = datetime.datetime.now()
        retval = _run_install_check_sql(schema, maddir_mod_py,
                                        module, sqlfile, tmpfile,
                                        logfile, pre_sql)
        # Runtime evaluation
        run_end = datetime.datetime.now()
        milliseconds = round((run_end - run_start).seconds * 1000 +
                             (run_end - run_start).microseconds / 1000)

        # Check the exit status
        result = _parse_result_logfile(retval, logfile, tmpfile, sqlfile,
                                       module, milliseconds)
    finally:
        # Cleanup test schema for the module
        _internal_run_query("DROP SCHEMA IF EXISTS %s CASCADE;" % (test_schema), True)


# ------------------------------------------------------------------------------
def _db_create_objects(schema, create_obj_handle, upgrade=False, sc=None):
    """
    Create MADlib DB objects in the schema
        @param schema Name of the target schema
        @param create_obj_handle file handle for sql output file
        @param upgrade flag to indicate if it's an upgrade operation or not
        @param sc ScriptCleaner object
    """
    if not upgrade:
        # Create MigrationHistory table
        try:
            _write_to_file(create_obj_handle,
                           "DROP TABLE IF EXISTS %s.migrationhistory;" % schema)
            sql = """CREATE TABLE %s.migrationhistory
                   (id serial, version varchar(255),
                    applied timestamp default current_timestamp);
                  """ % schema
            _write_to_file(create_obj_handle, sql)
        except:
            error_(this, "Cannot create MigrationHistory table", False)
            raise Exception

    # Stamp the DB installation
    try:
        _write_to_file(create_obj_handle,
                       """INSERT INTO %s.migrationhistory(version)
                            VALUES('%s');
                       """ % (schema, str(new_madlib_ver)))
    except:
        error_(this, "Cannot insert data into %s.migrationhistory table" % schema, False)
        raise Exception

    try:
        _write_to_file(create_obj_handle,
                       """SET dynamic_library_path = '%s';
                       """ % (dynamic_library_path))
    except:
        error_(this, "Cannot set dynamic_library_path to %s" % dynamic_library_path, False)
        raise Exception
    # Run migration SQLs
    info_(this, "> Preparing objects for the following modules:", True)
    # We always create objects for all modules during install/reinstall/upgrade
    modset = {}
    _process_py_sql_files_in_modules(modset, locals())

# ------------------------------------------------------------------------------

def unescape(string):
    """
    Unescape separation characters in connection strings, i.e., remove first
    backslash from "\/", "\@", "\:", and "\\".
    """
    if string is None:
        return None
    else:
        return re.sub(r'\\(?P<char>[/@:\\])', '\g<char>', string)
# ------------------------------------------------------------------------------

def parseConnectionStr(connectionStr):
    """
    @brief Parse connection strings of the form
           <tt>[username[/password]@][hostname][:port][/database]</tt>

    Separation characters (/@:) and the backslash (\) need to be escaped.
    @returns A tuple (username, password, hostname, port, database). Field not
             specified will be None.
    """
    match = re.search(
        r'((?P<user>([^/@:\\]|\\/|\\@|\\:|\\\\)+)' +
        r'(/(?P<password>([^/@:\\]|\\/|\\@|\\:|\\\\)*))?@)?' +
        r'(?P<host>([^/@:\\]|\\/|\\@|\\:|\\\\)+)?' +
        r'(:(?P<port>[0-9]+))?' +
        r'(/(?P<database>([^/@:\\]|\\/|\\@|\\:|\\\\)+))?', connectionStr)
    return (
        unescape(match.group('user')),
        unescape(match.group('password')),
        unescape(match.group('host')),
        match.group('port'),
        unescape(match.group('database')))
# ------------------------------------------------------------------------------

def parse_arguments():
    parser = argparse.ArgumentParser(
        prog="madpack",
        description='MADlib package manager (' + str(new_madlib_ver) + ')',
        argument_default=False,
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""Example:

  $ madpack install -s madlib -p greenplum -c gpadmin@mdw:5432/testdb

  This will install MADlib objects into a Greenplum database called TESTDB
  running on server MDW:5432. Installer will try to login as GPADMIN
  and will prompt for password. The target schema will be MADLIB.

  $ madpack dev-check

  This will run dev-check on all the installed modules in MADlib. Another
  similar, but light-weight check, is called install-check.

  $ madpack unit-test -t convex,recursive_partitioning/decision_tree

  This will run all the unit tests that are defined in the convex module, and
  for decision trees in the recursive partitioning module.
  The -t option runs tests only for required modules, and can be used similarly
  for install-check, dev-check and unit-test.
  """)

    help_msg = """One of the following options:
                  install        : load MADlib into DB
                  upgrade        : upgrade MADlib
                  uninstall      : uninstall MADlib from DB
                  reinstall      : perform uninstall and install
                  version        : compare and print MADlib version (binaries vs database objects)
                  install-check  : quick test of installed modules
                  dev-check      : more detailed test of installed modules
                  unit-test      : unit tests of installed modules
                  """
    choice_list = ['install', 'update', 'upgrade', 'uninstall',
                   'reinstall', 'version', 'install-check',
                   'dev-check', 'unit-test']

    parser.add_argument('command', metavar='COMMAND', nargs=1,
                        choices=choice_list, help=help_msg)

    parser.add_argument(
        '-c', '--conn', metavar='CONNSTR', nargs=1, dest='connstr', default=None,
        help="""Connection string of the following syntax:
                   [user[/password]@][host][:port][/database]
                 If not provided default values will be derived for PostgreSQL and Greenplum:
                 - user: PGUSER or USER env variable or OS username
                 - pass: PGPASSWORD env variable or runtime prompt
                 - host: PGHOST env variable or 'localhost'
                 - port: PGPORT env variable or '5432'
                 - db: PGDATABASE env variable or OS username""")

    parser.add_argument('-s', '--schema', nargs=1, dest='schema',
                        metavar='SCHEMA', default='madlib',
                        help="Target schema for the database objects.")

    parser.add_argument('-p', '--platform', nargs=1, dest='platform',
                        metavar='PLATFORM', choices=portid_list,
                        help="Target database platform, current choices: " + str(portid_list))

    parser.add_argument('-v', '--verbose', dest='verbose',
                        action="store_true", help="Verbose mode.")

    parser.add_argument('-l', '--keeplogs', dest='keeplogs', default=False,
                        action="store_true", help="Do not remove installation log files.")

    parser.add_argument('-d', '--tmpdir', dest='tmpdir', default='/tmp/',
                        help="Temporary directory location for installation log files.")

    parser.add_argument('-t', '--testcase', dest='testcase', default="",
                        help="Module names to test, comma separated. Applies to install-check, dev-check and unit-test.")

    # Get the arguments
    return parser.parse_args()

def _is_madlib_installation_valid_for_tests(schema, db_madlib_ver, test_type):
    # Compare OS and DB versions. Continue if OS = DB.
    if not db_madlib_ver:
        info_(this, "MADlib is not installed in the schema {0}. {1} stopped.".format(schema, test_type.capitalize()), True)
        return False
    if get_rev_num(db_madlib_ver) != get_rev_num(new_madlib_ver):
        _print_vers(new_madlib_ver, db_madlib_ver, con_args, schema)
        info_(this, "Versions do not match. {0} stopped.".format(test_type.capitalize()), True)
        return False
    return True

def _get_modset_for_tests(testcase, filename_prefix=''):
    # Get all module and algo names to run tests for, is specified as a comma
    # separated list.
    caseset = (set([test.strip() for test in testcase.split(',')])
               if testcase else set())
    modset = {}
    for case in caseset:
        if case.find('/') > -1:
            [mod, algo] = case.split('/')
            if mod not in modset:
                modset[mod] = []
            if algo not in modset[mod]:
                modset[mod].append(filename_prefix+algo)
        else:
            modset[case] = []
    return modset

def run_unit_tests(args, testcase):
    """
        Run unit tests.
    """
    if not _is_madlib_installation_valid_for_tests(args['schema'],
                                                   args['db_madlib_ver'],
                                                   'unit-tests'):
        return
    info_(this, "> Running unit-test scripts for:", verbose)
    modset = _get_modset_for_tests(testcase, 'test_')
    # Loop through all modules and run unit tests
    _process_py_sql_files_in_modules(modset, {'madpack_cmd': 'unit-test'})


def run_install_check(args, testcase, madpack_cmd):
    is_install_check = True if madpack_cmd == 'install-check' else False
    schema = args['schema']
    db_madlib_ver = args['db_madlib_ver']
    if not _is_madlib_installation_valid_for_tests(schema, db_madlib_ver, madpack_cmd):
        return
    # Create install-check user
    db_name = args["c_db"].replace('.', '').replace('-', '_').replace('"','""')
    test_user = ('madlib_' +
                 new_madlib_ver.replace('.', '').replace('-', '_') +
                 '_installcheck_' + db_name)
    try:
        _internal_run_query("DROP USER IF EXISTS \"%s\";" % (test_user), False)
    except Exception as e:
        _internal_run_query("DROP OWNED BY \"%s\" CASCADE;" % (test_user), True)
        _internal_run_query("DROP USER IF EXISTS \"%s\";" % (test_user), True)

    _internal_run_query("CREATE USER \"%s\"  WITH SUPERUSER NOINHERIT;" % (test_user), True)
    _internal_run_query("GRANT USAGE ON SCHEMA %s TO \"%s\";" % (schema, test_user), True)
    _internal_run_query("GRANT ALL PRIVILEGES ON DATABASE \"%s\" TO \"%s\";" % (db_name, test_user), True)

    # 2) Run test SQLs
    info_(this, "> Running %s scripts for:" % madpack_cmd, verbose)
    modset = _get_modset_for_tests(testcase)
    # Loop through all modules
    try:
        modset = _get_modset_for_tests(testcase)
        # Execute relevant sql files in each module for IC/DC
        _process_py_sql_files_in_modules(modset, locals())
    finally:
        # Drop install-check user
        _internal_run_query("REVOKE USAGE ON SCHEMA %s FROM \"%s\";" % (schema, test_user), True)
        try:
            _internal_run_query("DROP OWNED BY \"%s\" CASCADE;" % (test_user), show_error=False)
        except Exception as e:
            # We've intermittently noticed a "cache lookup failure" due to this
            # "DROP OWNED BY". This could be related to an error on
            # Stack Exchange: https://dba.stackexchange.com/questions/173815/redshift-internalerror-cache-lookup-failed-for-relation
            # Summary: Sometimes with too many drop statements the cache is
            # out-of-sync and takes a few seconds to resync. Repeat the same
            # command after a time gap.
            from time import sleep
            sleep(1)
            _internal_run_query("DROP OWNED BY \"%s\" CASCADE;" % (test_user), show_error=True)

        _internal_run_query("REVOKE ALL PRIVILEGES ON DATABASE \"%s\" FROM \"%s\";" % (db_name, test_user), True)
        _internal_run_query("DROP USER \"%s\";" % (test_user), True)


def _append_uninstall_madlib_sqlfile(schema, db_madlib_ver, is_schema_in_db,
                                     output_filehandle):
    if get_rev_num(db_madlib_ver) == [0]:
        info_(this,
              "Nothing to uninstall or reinstall. "
              "No version found in schema %s."% schema, True)
        return 1, is_schema_in_db

    # Find any potential data to lose
    affected_objects = _internal_run_query("""
        SELECT
            n1.nspname AS schema,
            relname AS relation,
            attname AS column,
            typname AS type
        FROM
            pg_attribute a,
            pg_class c,
            pg_type t,
            pg_namespace n,
            pg_namespace n1
        WHERE
            n.nspname = '%s'
            AND t.typnamespace = n.oid
            AND a.atttypid = t.oid
            AND c.oid = a.attrelid
            AND c.relnamespace = n1.oid
            AND c.relkind = 'r'
        ORDER BY
            n1.nspname, relname, attname, typname""" % schema.lower(), True)

    info_(this, "*** Uninstalling MADlib ***", True)
    info_(this, "***********************************************************************************", True)
    info_(this, "* Schema %s and all database objects depending on it will be dropped!" % schema, True)
    if affected_objects:
        info_(this, "* If you continue the following data will be lost (schema : table.column : type):", True)
        for ao in affected_objects:
            info_(this, '* - ' + ao['schema'] + ' : ' + ao['relation'] + '.' +
                  ao['column'] + ' : ' + ao['type'], True)
    info_(this, "***********************************************************************************", True)
    info_(this, "Would you like to continue? [Y/N]", True)
    go = raw_input('>>> ').upper()
    while (go not in ('Y', 'N', 'YES', 'NO')):
        go = raw_input('Yes or No >>> ').upper()

    # 2) Do the uninstall/drop
    if go in ('N', 'NO'):
        info_(this, 'No problem. Nothing dropped.', True)
        return 1, is_schema_in_db
    elif go in ('Y', 'YES'):
        try:
            _write_to_file(output_filehandle,
                           "DROP SCHEMA %s CASCADE;" % (schema))
            is_schema_in_db = False
            return 0, is_schema_in_db
        except:
            error_(this, "Cannot drop schema %s." % schema, True)

    else:
        return 1, is_schema_in_db

def _append_install_madlib_sqlfile(schema, db_madlib_ver, is_schema_in_db,
                                   madpack_cmd, output_filehandle):
    # Refresh MADlib version in DB, None for GP/PG
    if madpack_cmd == 'reinstall':
        info_(this, "Setting MADlib database version to be None for reinstall", verbose)
        db_madlib_ver = None

    info_(this, "*** Installing MADlib ***", True)

    # 1) Compare OS and DB versions.
    # noop if OS <= DB.
    _print_vers(new_madlib_ver, db_madlib_ver, con_args, schema)

    if db_madlib_ver is None:
        # Case when there is no existing MADlib installation, proceed to create
        # objects if nothing installed in DB
        pass
    elif is_rev_gte(get_rev_num(db_madlib_ver), get_rev_num(new_madlib_ver)):
        # Case when existing MADlib version is the same/higher as the new installation.
        info_(this, "Current MADlib version already up to date.", True)
        return 1
    else:
        # Case when the existing MADlib installation is lower than the new
        # installation. Error out and refer to upgrade if OS > DB
        error_(this, """Aborting installation: existing MADlib version detected in {0} schema
                To upgrade the {0} schema to MADlib v{1} please run the following command:
                madpack upgrade -s {0} -p {2} [-c ...]
                """.format(schema, new_madlib_ver, portid), True)

    # 2) Run installation
    _plpy_check(py_min_ver)
    _db_install(schema, is_schema_in_db, output_filehandle)
    return 0

def create_install_madlib_sqlfile(args, madpack_cmd):
    upgrade = args['upgrade']
    schema = args['schema']
    db_madlib_ver = args['db_madlib_ver']
    is_schema_in_db = args['is_schema_in_db']
    return_signal = 0
    with open(args['output_filename'], 'a+') as output_filehandle:
        # COMMAND: uninstall/reinstall
        if madpack_cmd in ('uninstall', 'reinstall'):
            return_signal, is_schema_in_db = _append_uninstall_madlib_sqlfile(
                schema, db_madlib_ver, is_schema_in_db, output_filehandle)
            if return_signal == 1:
                return 1

        # COMMAND: install/reinstall
        if madpack_cmd in ('install', 'reinstall'):
            return_signal += _append_install_madlib_sqlfile(schema, db_madlib_ver,
                is_schema_in_db, madpack_cmd, output_filehandle)

        # COMMAND: upgrade
        if madpack_cmd in ('upgrade', 'update'):
            upgrade = True
            info_(this, "*** Upgrading MADlib ***", True)
            db_madlib_ver = get_db_madlib_version(con_args, schema)

            # 1) Check DB version. If None, nothing to upgrade.
            if not db_madlib_ver:
                info_(this, "MADlib is not installed in {schema} schema and there "
                      "is nothing to upgrade. Please use install "
                      "instead.".format(schema=schema),
                      True)
                return_signal += 1

            # 2) Compare OS and DB versions. Continue if OS > DB.
            else:
                _print_vers(new_madlib_ver, db_madlib_ver, con_args, schema)
                if is_rev_gte(get_rev_num(db_madlib_ver), get_rev_num(new_madlib_ver)):
                    info_(this, "Current MADlib version is already up-to-date.", True)
                    return_signal += 1
                else:
                    # 3) Run upgrade
                    _plpy_check(py_min_ver)

                    return_signal = _db_upgrade(schema, output_filehandle, db_madlib_ver)

    return 1 if return_signal > 0 else 0

def get_madlib_function_drop_str(schema):

    if ((portid == 'greenplum' and is_rev_gte(get_rev_num(dbver), get_rev_num('7.0'))) or
        (portid == 'postgres')):
        case_str = """
        CASE p.prokind
          WHEN 'a' THEN 'aggregate'
          ELSE 'function'
          """
    else:
        case_str = """
        CASE
          WHEN p.proisagg THEN 'aggregate'
          ELSE 'function'
          """
    madlib_functions = _internal_run_query("""
        SELECT n.nspname as "Schema",
          p.proname as "name",
          pg_catalog.pg_get_function_arguments(p.oid) as "args",
         {0}
         END as "type"
        FROM pg_catalog.pg_proc p
             LEFT JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname OPERATOR(pg_catalog.~) '^({1})$'
        ORDER BY 4, 1, 2;
        """.format(case_str , schema.lower()), True)

    drop_str = ""

    for idx in range(len(madlib_functions)):

        func = madlib_functions[idx]

        # Filter out the DEFAULT value from the function arguments
        # DROP FUNCTION statements do not need or allow default values:
        # DROP FUNCTION foo(bar INTEGER DEFAULT 0);
        func['args'] = func['args'].split(',')
        func['args'] = [i.split('DEFAULT')[0] for i in func['args']]
        func['args'] = ', '.join(func['args'])

        # We don't drop type related functions
        no_drop = ['bytea8', 'float8arr', 'svec']
        if not any(x in func['name'] for x in no_drop):
            drop_str = drop_str + "DROP {0} {1}.{2}({3}); \n".format(
                func['type'], schema, func['name'], func['args'])

        # Break the drop file into chunks because some systems complain with long sql commands
        if idx%100 == 99:
            drop_str = drop_str + "\n"
    return drop_str


def get_madlib_operator_drop_str(schema):

    madlib_operators = _internal_run_query("""
        SELECT n.nspname as "Schema",
          o.oprname AS "name",
          CASE WHEN o.oprkind='l' THEN NULL
            ELSE pg_catalog.format_type(o.oprleft, NULL) END AS "left_op",
          CASE WHEN o.oprkind='r' THEN NULL
            ELSE pg_catalog.format_type(o.oprright, NULL) END AS "right_op"
        FROM pg_catalog.pg_operator o
             LEFT JOIN pg_catalog.pg_namespace n ON n.oid = o.oprnamespace
        WHERE n.nspname OPERATOR(pg_catalog.~) '^(%s)$'
        ORDER BY 1, 2, 3, 4;
        """ % schema.lower(), True)

    # Drop the Operator Class before the individual operators
    drop_str = "DROP OPERATOR CLASS IF EXISTS {0}.svec_ops USING btree; \n".format(schema)

    for i in madlib_operators:
        drop_str = drop_str + "DROP OPERATOR {0}.{1}({2},{3}); \n".format(
            schema, i['name'], i['left_op'], i['right_op'])
    return drop_str

def find_madlib_library_path():

    # Local build at ~/workspace/madlib/build/
    if os.path.isfile(maddir + "/../src/ports/" + portid + "/" + dbver +
                      "/lib/libmadlib.so"):
        madlib_library_path = maddir + "/../src/ports/" + portid + "/" + dbver + \
            "/lib"

    # Package build at /usr/local/madlib/Versions or $GPHOME/madlib/Versions
    elif os.path.isfile(maddir + "/../../Current/ports/" + portid + "/" + dbver +
                      "/lib/libmadlib.so"):
        madlib_library_path = maddir + "/../../Current/ports/" + portid + "/" + dbver + \
            "/lib"
    else:
        madlib_library_path = maddir + "/lib"

    return madlib_library_path

def set_dynamic_library_path_in_database(dbver_split, madlib_library_path):

    global dynamic_library_path
    dynamic_library_path = _internal_run_query("SHOW dynamic_library_path", True)[0]['dynamic_library_path']
    # GP7 gpconfig messes up $libdir so we put the actual path
    paths = dynamic_library_path.split(":")
    if madlib_library_path not in paths:
        if '$libdir' in paths:
            paths.remove('$libdir')
            libdir = subprocess.check_output(['pg_config','--libdir'])
            if ((portid == 'greenplum' and is_rev_gte(dbver_split, get_rev_num('7.0'))) or
                (portid == 'postgres' and is_rev_gte(dbver_split, get_rev_num('13.0')))):
                libdir = libdir.decode()

            libdir = libdir.strip()+'/postgresql'
            paths.append(libdir)

        paths.append(madlib_library_path)
        dynamic_library_path = ':'.join(paths)

        if portid == 'greenplum':
            if is_rev_gte(dbver_split, get_rev_num('6.0')):
                ret = os.system('gpconfig -c dynamic_library_path -v \'{0}\''.format(dynamic_library_path))
            else:
                ret = os.system('gpconfig -c dynamic_library_path -v \'\\{0}\''.format(dynamic_library_path))
            ret = ret + os.system('gpstop -u')
            if ret != 0:
                error_(this, "cannot run gpconfig or gpstop", True)
        else:
            _internal_run_query(
                "ALTER SYSTEM SET dynamic_library_path TO '{0}'".format(dynamic_library_path), True)
            pg_data_directory = _internal_run_query("SHOW data_directory", True)[0]['data_directory']
            ret = os.system('pg_ctl -D {0} reload'.format(pg_data_directory))
            if ret != 0:
                error_(this, "cannot run pg_ctl", True)


def main(argv):
    args = parse_arguments()

    global verbose
    verbose = args.verbose
    info_(this, "Arguments: " + str(args), verbose)
    global keeplogs
    keeplogs = args.keeplogs

    global tmpdir
    try:
        tmpdir = tempfile.mkdtemp('', 'madlib.', args.tmpdir)
    except OSError as e:
        tmpdir = e.filename
        error_(this, "cannot create temporary directory: '%s'." % tmpdir, True)

    # Parse SCHEMA
    if len(args.schema[0]) > 1:
        schema = args.schema[0].lower()
    else:
        schema = args.schema.lower()
    # Parse DB Platform (== PortID) and compare with Ports.yml
    global portid
    if args.platform:
        try:
            # Get the DB platform name == DB port id
            portid = args.platform[0].lower()
            ports[portid]
        except:
            portid = None
            error_(this, "Can not find specs for port %s" % (args.platform[0]), True)
    else:
        portid = None

    # Parse CONNSTR (only if PLATFORM and DBAPI2 are defined)
    if portid:
        connStr = "" if args.connstr is None else args.connstr[0]
        (c_user, c_pass, c_host, c_port, c_db) = parseConnectionStr(connStr)

        # Find the default values for PG and GP
        if portid in SUPPORTED_PORTS:
            if c_user is None:
                c_user = os.environ.get('PGUSER', getpass.getuser())
            if c_pass is None:
                c_pass = os.environ.get('PGPASSWORD', None)
            if c_host is None:
                c_host = os.environ.get('PGHOST', 'localhost')
            if c_port is None:
                c_port = os.environ.get('PGPORT', '5432')
            if c_db is None:
                c_db = os.environ.get('PGDATABASE', c_user)

        # Set connection variables
        global con_args
        con_args['host'] = c_host + ':' + c_port
        con_args['database'] = c_db
        con_args['user'] = c_user
        if c_pass is not None:
            con_args['password'] = c_pass

        # Try connecting to the database
        info_(this, "Testing database connection...", verbose)

        try:
            # check for password only if required
            _internal_run_query("SELECT 1", False)
        except EnvironmentError:
            con_args['password'] = getpass.getpass("Password for user %s: " % c_user)
            _internal_run_query("SELECT 1", False)
        except:
            error_(this, 'Failed to connect to database', True)

        # Get DB version
        global dbver
        dbver = get_dbver(con_args, portid)

        # update maddir to use a relative path if available
        global maddir
        maddir = _get_relative_maddir(maddir, portid)

        # Get MADlib version in DB
        db_madlib_ver = get_db_madlib_version(con_args, schema)

        portdir = os.path.join(maddir, "ports", portid)
        supportedVersions = [dirItem for dirItem in os.listdir(portdir)
                             if os.path.isdir(os.path.join(portdir, dirItem)) and
                             re.match("^\d+", dirItem)]

        if dbver is None:
            dbver = ".".join(
                map(str, max([versionStr.split('.')
                              for versionStr in supportedVersions])))
            info_(this, "Could not parse version string reported by {DBMS}. Will "
                  "default to newest supported version of {DBMS} "
                  "({version}).".format(DBMS=ports[portid]['name'],
                                        version=dbver), True)
        else:
            info_(this, "Detected %s version %s." % (ports[portid]['name'], dbver),
                  True)

            dbver_split = get_rev_num(dbver)
            if portid == 'greenplum':
                if is_rev_gte(dbver_split, get_rev_num('5.0')):
                    # GPDB (starting 5.0) uses semantic versioning. Hence, only
                    # need first digit for major version.
                    dbver = str(dbver_split[0])
                elif is_rev_gte(dbver_split, get_rev_num('4.3.5')):
                    # Due to the ABI incompatibility between 4.3.4 and 4.3.5,
                    # MADlib treats 4.3.5+ as DB version 4.3ORCA which is
                    # different from 4.3. The name is suffixed with ORCA since
                    # optimizer (ORCA) is 'on' by default in 4.3.5+
                    dbver = '4.3ORCA'
                else:
                    # only need the first two digits for <= 4.3.4
                    dbver = '.'.join(map(str, dbver_split[:2]))
            elif portid == 'postgres':
                if is_rev_gte(dbver_split, get_rev_num('10.0')):
                    # Postgres starting 10.0 uses semantic versioning. Hence,
                    # only need first digit for major version.
                    dbver = str(dbver_split[0])
            if not os.path.isdir(os.path.join(portdir, dbver)):
                error_(this, "This version is not among the %s versions for which "
                       "MADlib support files have been installed (%s)." %
                       (ports[portid]['name'], ", ".join(supportedVersions)), True)

        # Validate that db platform is correct
        if not _check_db_port(portid):
            error_(this, "Invalid database platform specified.", True)

        # Adjust MADlib directories for this port (if they exist)
        global maddir_conf
        if os.path.isdir(maddir + "/ports/" + portid + "/" + dbver + "/config"):
            maddir_conf = maddir + "/ports/" + portid + "/" + dbver + "/config"
        else:
            maddir_conf = maddir + "/config"

        global madlib_library_path
        madlib_library_path = find_madlib_library_path()
        set_dynamic_library_path_in_database(dbver_split, madlib_library_path)

        # Get the list of modules for this port
        global portspecs
        portspecs = configyml.get_modules(maddir_conf)
    else:
        con_args = None
        db_madlib_ver = None

    # Parse COMMAND argument and compare with Ports.yml
    # Debugging...
    # print "OS new_madlib_ver: " + str(new_madlib_ver) + " > " + str(get_rev_num(new_madlib_ver))
    # print "DB new_madlib_ver: " + str(db_madlib_ver) + " > " + str(get_rev_num(db_madlib_ver))

    # Make sure we have the necessary parameters to continue
    if args.command[0] != 'version':
        if not portid:
            error_(this, "Missing -p/--platform parameter.", True)
        if not con_args:
            error_(this, "Unknown problem with database connection string: %s" % con_args, True)
    # ---------------- Completed "Get and validate arguments" -----------------


    # COMMAND: install-check, dev-check or unit-test
    if args.command[0] in ('install-check', 'dev-check'):
        run_install_check(locals(), args.testcase, args.command[0])
    elif args.command[0] == 'unit-test':
        run_unit_tests(locals(), args.testcase)
    elif args.command[0] == 'version':
        _print_vers(new_madlib_ver, db_madlib_ver, con_args, schema)
    else:
        if args.testcase:
            error_(this,
                   "-t (testcase) option is not supported for %s" % args.command[0],
                   True)
        try:
            is_schema_in_db = _internal_run_query("SELECT schema_name FROM information_schema.schemata WHERE schema_name='%s';" % schema, True)
        except:
            error_(this, "Cannot validate if schema already exists.", True)

        output_filename = tmpdir + "/madlib_{0}.sql".format(args.command[0])
        upgrade = False
        return_val = create_install_madlib_sqlfile(locals(), args.command[0])
        if return_val == 0:
            op_msg = (args.command[0].capitalize() + "ing"
                      if args.command[0] != 'upgrade'
                      else 'Upgrading')
            info_(this, "%s MADlib:" % op_msg, True)
            _cleanup_comments_in_sqlfile(output_filename, upgrade)
            result = _run_sql_file(schema, output_filename)
            if result == 'FAIL':
                info_(this, "MADlib {0} unsuccessful.".format(args.command[0]), True)
                info_(this, "All changes are rolled back.", True)
            else:
                if args.command[0] != 'uninstall':
                    if args.command[0] == 'upgrade':
                        info_(this, "MADlib %s upgraded successfully in %s schema." % (str(new_madlib_ver), schema), True)
                    else:
                        info_(this, "> Created %s schema" % schema, True)
                        info_(this, "> Created %s.MigrationHistory table" % schema, True)
                        info_(this, "> Wrote version info in MigrationHistory table", True)
                        info_(this, "MADlib %s installed successfully in %s schema." % (str(new_madlib_ver), schema))
                else:
                    info_(this, "MADlib %s uninstalled successfully from %s schema." % (str(new_madlib_ver), schema))


# ------------------------------------------------------------------------------
# Start Here
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    # Run main
    main(sys.argv[1:])

    # Optional log files cleanup
    # keeplogs and tmpdir are global variables
    if not keeplogs:
        shutil.rmtree(tmpdir)
    else:
        print("INFO: Log files saved in " + tmpdir)
