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

CREATE OR REPLACE FUNCTION get_udocs(table_name text, schema_name text,
                                         type_filter text)
RETURNS VOID AS
$$
    import plpy

    plpy.execute("""
	CREATE TABLE {table_name} AS
	SELECT * FROM (
		SELECT index_method, opfamily_name,
			   array_to_string(array_agg(alter_schema(opfamily_operator::text, '{schema_name}')), ',')
			   	AS operators
		FROM (
			SELECT am.amname AS index_method, opf.opfname AS opfamily_name,
		       	   amop.amopopr::regoperator AS opfamily_operator
		    FROM pg_am am, pg_opfamily opf, pg_amop amop, pg_namespace n
		    WHERE opf.opfmethod = am.oid AND
		          amop.amopfamily = opf.oid AND
		          n.oid = opf.opfnamespace AND
		          n.nspname OPERATOR(pg_catalog.~) '^({schema_name})$'
		    ORDER BY index_method, opfamily_name, opfamily_operator
		    ) q
		GROUP BY (index_method, opfamily_name)
		) qq
	WHERE operators LIKE '%schema_madlib.{type_filter}%' OR '{type_filter}' LIKE 'Full'
	""".format(table_name=table_name, schema_name=schema_name, type_filter=type_filter))

$$ LANGUAGE plpython3u;

DROP TABLE if exists udoc_madlib_old_version;
DROP TABLE if exists udoc_madlib_new_version;

SELECT get_udocs('udoc_madlib_old_version','madlib_old_vers','Full');
SELECT get_udocs('udoc_madlib_new_version','madlib','Full');


SELECT old1.opfamily_name, old1.index_method
FROM udoc_madlib_old_version AS old1 LEFT JOIN udoc_madlib_new_version
	USING (index_method, opfamily_name, operators)
WHERE udoc_madlib_new_version.opfamily_name is NULL
ORDER BY 1;

