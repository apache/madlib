/* ----------------------------------------------------------------------- *//**
 *
 * @file dbconnector.hpp
 *
 * @brief This file should be included by user code (and nothing else)
 *
 *//* ----------------------------------------------------------------------- */

#ifndef MADLIB_GREENPLUM_DBCONNECTOR_HPP
#define MADLIB_GREENPLUM_DBCONNECTOR_HPP

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
    #include <utils/builtins.h>    // needed for format_procedure()
    #include <utils/datum.h>
    #include <utils/lsyscache.h>   // for type lookup, e.g., type_is_rowtype
    #include <utils/memutils.h>
    #include <utils/syscache.h>    // for direct access to catalog, e.g., SearchSysCache()
    #include <utils/typcache.h>    // type conversion, e.g., lookup_rowtype_tupdesc
    #include "../../../../methods/svec/src/pg_gp/sparse_vector.h" // Legacy sparse vectors
} // extern "C"

#include "Compatibility.hpp"

#if GP_VERSION_NUM >= 60000
    // MADlib aligns the pointers returned by palloc() to 16-byte boundaries
    // (see Allocator_impl.hpp). This is done to allow Eigen vectorization  (see
    // http://eigen.tuxfamily.org/index.php?title=FAQ#Vectorization for more
    // info).  This vectorization has to be explicitly disabled if pointers are
    // not 16-byte aligned. Further, the pointer realignment invalidates a
    // header that palloc creates just prior to the pointer address.  Greenplum
    // after commit f62bd1c fails due to this invalid header.  Hence, the
    // pointer realignment and Eigen vectorization is disabled below for
    // Greenplum 6 and above.

    // See http://eigen.tuxfamily.org/dox/group__TopicUnalignedArrayAssert.html
    // for steps to disable vectorization
    #define EIGEN_DONT_VECTORIZE
    #define EIGEN_DISABLE_UNALIGNED_ARRAY_ASSERT
#endif

#include "../../postgres/dbconnector/dbconnector.hpp"

#endif // defined(MADLIB_GREENPLUM_DBCONNECTOR_HPP)
