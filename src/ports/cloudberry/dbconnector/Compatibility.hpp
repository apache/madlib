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
 * @file cloudberry/dbconnector/Compatibility.cpp
 *
 *//* ----------------------------------------------------------------------- */

#ifndef MADLIB_CLOUDBERRY_COMPATIBILITY_HPP
#define MADLIB_CLOUDBERRY_COMPATIBILITY_HPP

namespace madlib {

namespace dbconnector {

namespace postgres {

namespace {
// No need to make these function accessible outside of the postgres namespace.

#ifndef PG_GET_COLLATION
// Greenplum does not currently have support for collations
#define PG_GET_COLLATION()	InvalidOid
#endif

#ifndef SearchSysCache1
// See madlib_SearchSysCache1()
#define SearchSysCache1(cacheId, key1) \
	SearchSysCache(cacheId, key1, 0, 0, 0)
#endif

} // namespace

inline ArrayType* madlib_construct_array
	(
		Datum*  elems,
		int     nelems,
		Oid     elmtype,
		int     elmlen,
		bool    elmbyval,
		char    elmalign
	){
	return
		construct_array(
			elems, nelems, elmtype, elmlen, elmbyval, elmalign);
}

inline ArrayType* madlib_construct_md_array
	(
		Datum*  elems,
		bool*   nulls,
		int     ndims,
		int*    dims,
		int*    lbs,
		Oid     elmtype,
		int     elmlen,
		bool    elmbyval,
		char    elmalign
	){
	return
		construct_md_array(
			elems, nulls, ndims, dims, lbs, elmtype, elmlen, elmbyval,
			elmalign);
}

} // namespace postgres

} // namespace dbconnector

} // namespace madlib

#endif // defined(MADLIB_CLOUDBERRY_COMPATIBILITY_HPP)
