/* ----------------------------------------------------------------------- *//**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 * 
 * @file dbconnector.hpp
 *
 * @brief This file should be included by user code (and nothing else)
 *
 *//* ----------------------------------------------------------------------- */

#ifndef MADLIB_CLOUDBERRY_DBCONNECTOR_HPP
#define MADLIB_CLOUDBERRY_DBCONNECTOR_HPP

// On platforms based on PostgreSQL we can include a different set of headers.
#define MADLIB_POSTGRES_HEADERS

extern "C" {
#include <postgres.h>
#include <funcapi.h>
#include <catalog/pg_proc.h>
#include <catalog/pg_type.h>
#include <executor/executor.h> // Greenplum requires this for GetAttributeByNum()
#include <miscadmin.h>         // Memory allocation, e.g., HOLD_INTERRUPTS
#include <utils/acl.h>
#include <utils/array.h>
#include <utils/builtins.h>   // needed for string_to_text()、cstring_to_text_with_len()
#include <utils/elog.h>       // needed for errstart_cold
#include <utils/regproc.h>    // needed for format_procedure()
#include <common/hashfn.h>    // needed for oid_hash
#include <utils/datum.h>
#include <utils/lsyscache.h>   // for type lookup, e.g., type_is_rowtype
#include <utils/memutils.h>
#include <utils/syscache.h>    // for direct access to catalog, e.g., SearchSysCache()
#include <utils/typcache.h>    // type conversion, e.g., lookup_rowtype_tupdesc
#include "../../../../methods/svec/src/pg_gp/sparse_vector.h" // Legacy sparse vectors
} // extern "C"

Datum drandom(PG_FUNCTION_ARGS);
Datum setseed(PG_FUNCTION_ARGS);

#ifdef sprintf
#undef sprintf
#endif

#ifdef snprintf
#undef snprintf
#endif

#include "Compatibility.hpp"

#include "../../postgres/dbconnector/dbconnector.hpp"

#endif // defined(MADLIB_CLOUDBERRY_DBCONNECTOR_HPP)
