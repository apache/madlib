------------------------------------------------------------------------------
-- Licensed to the Apache Software Foundation (ASF) under one
-- or more contributor license agreements.  See the NOTICE file
-- distributed with this work for additional information
-- regarding copyright ownership.  The ASF licenses this file
-- to you under the Apache License, Version 2.0 (the
-- "License"); you may not use this file except in compliance
-- with the License.  You may obtain a copy of the License at

--   http://www.apache.org/licenses/LICENSE-2.0

-- Unless required by applicable law or agreed to in writing,
-- software distributed under the License is distributed on an
-- "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
-- KIND, either express or implied.  See the License for the
-- specific language governing permissions and limitations
-- under the License.
------------------------------------------------------------------------------

SET client_min_messages to ERROR;
\x on

CREATE OR REPLACE FUNCTION filter_schema(argstr text, schema_name text)
RETURNS text AS $$
    if argstr is None:
        return "NULL"
    return argstr.replace(schema_name + ".", '')
$$ LANGUAGE plpython3u;

CREATE OR REPLACE FUNCTION alter_schema(argstr text, schema_name text)
RETURNS text AS $$
    if argstr is None:
        return "NULL"
    return argstr.replace(schema_name + ".", 'schema_madlib.')
$$ LANGUAGE plpython3u;


CREATE OR REPLACE FUNCTION get_udos(table_name text, schema_name text,
                                         type_filter text)
RETURNS VOID AS
$$
    import plpy

    plpy.execute("""
        create table {table_name} AS
            SELECT *
            FROM (
                SELECT n.nspname AS "Schema",
                       o.oprname AS name,
                       filter_schema(o.oprcode::text, '{schema_name}') AS oprcode,
                       alter_schema(pg_catalog.format_type(o.oprleft, NULL), '{schema_name}') AS oprleft,
                       alter_schema(pg_catalog.format_type(o.oprright, NULL), '{schema_name}') AS oprright,
                       alter_schema(pg_catalog.format_type(o.oprresult, NULL), '{schema_name}') AS rettype
                FROM pg_catalog.pg_operator o
                    LEFT JOIN pg_catalog.pg_namespace n ON n.oid = o.oprnamespace
                WHERE n.nspname OPERATOR(pg_catalog.~) '^({schema_name})$'
                ) q
            WHERE oprleft LIKE 'schema_madlib.{type_filter}'
                  OR oprleft LIKE 'schema_madlib.{type_filter}[]'
                  OR oprright LIKE 'schema_madlib.{type_filter}'
                  OR oprright LIKE 'schema_madlib.{type_filter}[]'
                  OR rettype LIKE 'schema_madlib.{type_filter}'
                  OR rettype LIKE 'schema_madlib.{type_filter}[]'
                  OR '{type_filter}' LIKE 'Full'
    """.format(table_name=table_name, schema_name=schema_name, type_filter=type_filter))
$$ LANGUAGE plpython3u;


DROP TABLE if exists udo_madlib_old_version;
DROP TABLE if exists udo_madlib_new_version;

SELECT get_udos('udo_madlib_old_version','madlib_old_vers','Full');
SELECT get_udos('udo_madlib_new_version','madlib','Full');


SELECT old1.name AS name , old1.oprright AS oprright,
       old1.oprleft AS oprleft, old1.rettype AS rettype
FROM udo_madlib_old_version AS old1 LEFT JOIN udo_madlib_new_version
    USING (name, oprcode, oprright, oprleft, rettype)
WHERE udo_madlib_new_version.name is NULL
ORDER BY old1.name;
