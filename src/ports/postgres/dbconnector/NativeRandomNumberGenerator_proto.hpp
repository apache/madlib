/* ----------------------------------------------------------------------- *//**
 *
 * @file NativeRandomNumberGenerator_proto.hpp
 *
 *//* ----------------------------------------------------------------------- */

#ifndef MADLIB_POSTGRES_NATIVERANDOMNUMBERGENERATOR_PROTO_HPP
#define MADLIB_POSTGRES_NATIVERANDOMNUMBERGENERATOR_PROTO_HPP

namespace madlib {

namespace dbconnector {

namespace postgres {

/**
 * @brief Front-end to the RDBMS random number generator
 *
 * This pseudo-RNG is special in that it has no own state. Instead, its state is
 * externally defined. It is therefore not necessary to keep a global instance
 * of this RNG.
 */
class NativeRandomNumberGenerator {
public:
    typedef double result_type;

#if _GLIBCXX_USE_CXX11_ABI
#define CONST_EXPR constexpr
#else
#define CONST_EXPR
#endif

    NativeRandomNumberGenerator();
    void seed(result_type inSeed);
    result_type operator()();
    static CONST_EXPR result_type min();
    static CONST_EXPR result_type max();
};

} // namespace postgres

} // namespace dbconnector

} // namespace madlib

#endif // defined(MADLIB_POSTGRES_NATIVERANDOMNUMBERGENERATOR_PROTO_HPP)
