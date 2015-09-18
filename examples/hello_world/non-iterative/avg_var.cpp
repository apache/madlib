/* ----------------------------------------------------------------------- *//**
 *
 * @file linear.cpp
 *
 * @brief average population variance functions
 *
 *//* ----------------------------------------------------------------------- */

#include <dbconnector/dbconnector.hpp>
#include <modules/shared/HandleTraits.hpp>
#include "avg_var.hpp"

namespace madlib {

namespace modules {

namespace hello_world {

template <class Handle>
class AvgVarTransitionState {
	template <class OtherHandle>
    friend class AvgVarTransitionState;

  public:
    AvgVarTransitionState(const AnyType &inArray)
        : mStorage(inArray.getAs<Handle>()) {

        rebind();
    }

    /**
     * @brief Convert to backend representation
     *
     * We define this function so that we can use State in the
     * argument list and as a return type.
     */
    inline operator AnyType() const {
        return mStorage;
    }

    /**
     * @brief Merge with another State object
     *
     * We update mean and variance in a online fashion
     * to avoid intermediate large sum. 
     */
    template <class OtherHandle>
    AvgVarTransitionState &operator+=(
        const AvgVarTransitionState<OtherHandle> &inOtherState) {

        if (mStorage.size() != inOtherState.mStorage.size())
            throw std::logic_error("Internal error: Incompatible transition "
                                   "states");
        double avg_ = inOtherState.avg;
        double var_ = inOtherState.var;
        uint16_t numRows_ = static_cast<uint16_t>(inOtherState.numRows);
        double totalNumRows = static_cast<double>(numRows + numRows_);
        double p = static_cast<double>(numRows) / totalNumRows;
        double p_ = static_cast<double>(numRows_) / totalNumRows;
        double totalAvg = avg * p + avg_ * p_;
        double a = avg - totalAvg;
        double a_ = avg_ - totalAvg;

        numRows += numRows_;
        var = p * var + p_ * var_ + p * a * a + p_ * a_ * a_;
        avg = totalAvg;
        return *this;
    }

  private:
    void rebind() {
        avg.rebind(&mStorage[0]);
        var.rebind(&mStorage[1]);
        numRows.rebind(&mStorage[2]);
    }

    Handle mStorage;

  public:
    typename HandleTraits<Handle>::ReferenceToDouble avg;
    typename HandleTraits<Handle>::ReferenceToDouble var;
    typename HandleTraits<Handle>::ReferenceToUInt64 numRows;
};


AnyType
avg_var_transition::run(AnyType& args) {
    // get current state value 
    AvgVarTransitionState<MutableArrayHandle<double> > state = args[0];
    // get current row value
    double x = args[1].getAs<double>();
    double d_ = (x - state.avg);
    // online update mean
    state.avg += d_ / static_cast<double>(state.numRows + 1);
    double d = (x - state.avg);
    double a = static_cast<double>(state.numRows) / static_cast<double>(state.numRows + 1);
    // online update variance
    state.var = state.var * a + d_ * d / static_cast<double>(state.numRows + 1);
    state.numRows ++;
    return state;
}

AnyType
avg_var_merge_states::run(AnyType& args) {
    AvgVarTransitionState<MutableArrayHandle<double> > stateLeft = args[0];
    AvgVarTransitionState<ArrayHandle<double> > stateRight = args[1];

    // Merge states together and return
    stateLeft += stateRight;
    return stateLeft;
}

AnyType
avg_var_final::run(AnyType& args) {
    AvgVarTransitionState<MutableArrayHandle<double> > state = args[0];

    // If we haven't seen any data, just return Null. This is the standard
    // behavior of aggregate function on empty data sets (compare, e.g.,
    // how PostgreSQL handles sum or avg on empty inputs)
    if (state.numRows == 0)
        return Null();

    return state;
}
// -----------------------------------------------------------------------

} // namespace hello_world
} // namespace modules
} // namespace madlib
