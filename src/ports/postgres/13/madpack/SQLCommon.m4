/*
 * PostgreSQL include file for sql_in files.
 */

/*
 * During build time, macro definitions will be inserted here.
 */
m4_define(`__POSTGRESQL__')
m4_define(`__PORT__', `POSTGRESQL')
m4_define(`__DBMS__', `postgresql_13')
m4_define(`__DBMS_VERSION__', `13.3.0')
m4_define(`__DBMS_VERSION_MAJOR__', `13')
m4_define(`__DBMS_VERSION_MINOR__', `3')
m4_define(`__DBMS_VERSION_PATCH__', `0')
m4_define(`__DBMS_ARCHITECTURE__', `x86_64')
m4_define(`__MADLIB_VERSION__', `1.19.0-dev')
m4_define(`__MADLIB_VERSION_MAJOR__', `1')
m4_define(`__MADLIB_VERSION_MINOR__', `19')
m4_define(`__MADLIB_VERSION_PATCH__', `0')
m4_define(`__MADLIB_GIT_REVISION__', `rel/v1.18.0-9-g798de717')
m4_define(`__MADLIB_BUILD_TIME__', `Sat Aug 21 13:35:02 UTC 2021')
m4_define(`__MADLIB_BUILD_TYPE__', `Release')
m4_define(`__MADLIB_BUILD_SYSTEM__', `Linux-5.4.0-77-generic')
m4_define(`__MADLIB_C_COMPILER__', `gcc 9')
m4_define(`__MADLIB_CXX_COMPILER__', `g++ 9')
m4_define(`__HAS_ORDERED_AGGREGATES__')
m4_define(`__HAS_BOOL_TO_TEXT_CAST__')

/*
 * There is no way in m4 to escape the quote characters, so we change it
 * temporarily to something different than the default.
 */
m4_changequote(<!,!>)

/*
 * PythonFunction
 *
 * @param $1 directory
 * @param $2 python file (without suffix)
 * @param $3 function
 *
 * Example:
 * CREATE FUNCTION MADLIB_SCHEMA.logregr_coef(
 *     "source" VARCHAR,
 *     "depColumn" VARCHAR,
 *     "indepColumn" VARCHAR)
 * RETURNS DOUBLE PRECISION[]
 * AS $$PythonFunction(regress, logistic, compute_logregr_coef)$$
 * LANGUAGE plpythonu VOLATILE;
 */
m4_define(<!PythonFunction!>, <!
    import sys
    from inspect import getframeinfo, currentframe
    sys.path.insert(1, "EXT_PYTHON_LIBDIR")
    sys.path.insert(1, "PLPYTHON_LIBDIR")
    from $1 import $2

    # Retrieve the schema name of the current function
    # Make it available as variable: schema_madlib
    fname = getframeinfo(currentframe()).function
    foid  = fname.rsplit('_',1)[1]

    # plpython names its functions "__plpython_procedure_<function name>_<oid>",
    # of which we want the oid
    rv = plpy.execute('SELECT nspname, proname FROM pg_proc p ' \
         'JOIN pg_namespace n ON (p.pronamespace = n.oid) ' \
         'WHERE p.oid = %s' % foid, 1)

    global schema_madlib
    schema_madlib = rv[0]['nspname']

    from utilities.control import AOControl
    with AOControl(False):
        return $2.$3(**globals())
!>)

/*
 * PythonFunctionBodyOnly
 *
 * @param $1 directory
 * @param $2 python file (without suffix)
 *
 */
m4_define(<!PythonFunctionBodyOnly!>, <!
    import sys
    from inspect import getframeinfo, currentframe
    sys.path.insert(1, "EXT_PYTHON_LIBDIR")
    sys.path.insert(1, "PLPYTHON_LIBDIR")
    from $1 import $2

    # Retrieve the schema name of the current function
    # Make it available as variable: schema_madlib
    fname = getframeinfo(currentframe()).function
    foid  = fname.rsplit('_',1)[1]

    # plpython names its functions "__plpython_procedure_<function name>_<oid>",
    # of which we want the oid
    rv = plpy.execute('SELECT nspname, proname FROM pg_proc p ' \
         'JOIN pg_namespace n ON (p.pronamespace = n.oid) ' \
         'WHERE p.oid = %s' % foid, 1)

    global schema_madlib
    schema_madlib = rv[0]['nspname']
    from utilities.control import AOControl,MinWarning
!>)

/*
 * PythonFunctionBodyOnlyNoSchema
 *
 * @param $1 directory
 * @param $2 python file (without suffix)
 *
 */
m4_define(<!PythonFunctionBodyOnlyNoSchema!>, <!
    import sys
    sys.path.insert(1, "EXT_PYTHON_LIBDIR")
    sys.path.insert(1, "PLPYTHON_LIBDIR")
    from $1 import $2
!>)

/*
 * Change the quote character back to their defaults.
 */
m4_changequote(<!`!>,<!'!>)
