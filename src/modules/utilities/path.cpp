/* ----------------------------------------------------------------------- *//**
 * @file path.cpp
 *
 *//* ----------------------------------------------------------------------- */
#include <dbconnector/dbconnector.hpp>
#include <modules/shared/HandleTraits.hpp>

#include <math.h>
#include <iostream>
#include <algorithm>
#include <functional>
#include <numeric>
#include <vector>
#include <string>
#include <boost/generator_iterator.hpp>
#include <boost/regex.hpp>
#include "path.hpp"

namespace madlib {
namespace modules {
namespace utilities {

// using madlib::dbconnector::postgres::madlib_get_typlenbyvalalign;
// using madlib::dbconnector::postgres::madlib_construct_array;
// using madlib::dbconnector::postgres::madlib_construct_md_array;

// Use Eigen
using namespace dbal::eigen_integration;

AnyType path_pattern_match::run(AnyType & args)
{
    std::string sym_str = args[0].getAs<char *>();
    std::string reg_str = args[1].getAs<char *>();
    MappedColumnVector row_id = args[2].getAs<MappedColumnVector>();

    if (sym_str.size() != row_id.size()) {
        std::stringstream errorMsg;
        errorMsg << "dimensions mismatch: " << sym_str.size() <<
                    " != " << row_id.size() <<
                    "; #symbols must be equal to #rows!";
        throw std::invalid_argument(errorMsg.str());
    }

    boost::regex reg(reg_str);
    boost::smatch matches;
    std::string::const_iterator start0 = sym_str.begin(),
                                start = sym_str.begin(),
                                end = sym_str.end();

    int match_count = 0;
    while (boost::regex_search(start, end, matches, reg)) {
        match_count += matches[0].length();
        start = matches[0].second;
    }

    ColumnVector match_id(match_count);
    ColumnVector match_row_id(match_count);
    start = start0;
    match_count = 1;
    int idx = 0;
    while (boost::regex_search(start, end, matches, reg)) {
        // database represents array in [1, array_dim]
        int i0 = matches[0].first - start0;
        int i1 = i0 + matches[0].length();
        for (int i = i0; i < i1; i++, idx++) {
            match_row_id[idx] = row_id[i];
            match_id[idx] = match_count;
        }
        match_count++;
        start = matches[0].second;
    }

    AnyType tuple;
    tuple << match_id << match_row_id;
    return tuple;
}

} // namespace utilities
} // namespace modules
} // namespace madlib
