/* ----------------------------------------------------------------------- *//**
 *
 * @file model.hpp
 *
 * This file contians classes of coefficients (or model), which usually has
 * fields that maps to transition states for user-defined aggregates.
 * The necessity of these wrappers is to allow classes in algo/ and task/ to
 * have a type that they can template over.
 *
 *//* ----------------------------------------------------------------------- */

#ifndef MADLIB_MODULES_CONVEX_TYPE_MODEL_HPP_
#define MADLIB_MODULES_CONVEX_TYPE_MODEL_HPP_

#include <modules/shared/HandleTraits.hpp>

namespace madlib {

namespace modules {

namespace convex {

template <class Handle>
struct LMFModel {
    typename HandleTraits<Handle>::MatrixTransparentHandleMap matrixU;
    typename HandleTraits<Handle>::MatrixTransparentHandleMap matrixV;

    /**
     * @brief Space needed.
     *
     * Extra information besides the values in the matrix, like dimension is
     * necessary for a matrix, so that it can perform operations. These are
     * stored in the HandleMap.
     */
    static inline uint32_t arraySize(const int32_t inRowDim,
            const int32_t inColDim, const int32_t inMaxRank) {
        return (inRowDim + inColDim) * inMaxRank;
    }

    /**
     * @brief Initialize the model randomly with a user-provided scale factor
     */
    void initialize(const double &inScaleFactor) {
        // using madlib::dbconnector::$database::NativeRandomNumberGenerator
        NativeRandomNumberGenerator rng;
        int i, j, rr;
        double base = rng.min();
        double span = rng.max() - base;
        for (rr = 0; rr < matrixU.cols(); rr ++) {
            for (i = 0; i < matrixU.rows(); i ++) {
                matrixU(i, rr) = inScaleFactor * (rng() - base) / span;
            }
        }
        for (rr = 0; rr < matrixV.cols(); rr ++) {
            for (j = 0; j < matrixV.rows(); j ++) {
                matrixV(j, rr) = inScaleFactor * (rng() - base) / span;
            }
        }
    }

    /*
     *  Some operator wrappers for two matrices.
     */
    LMFModel &operator*=(const double &c) {
        matrixU *= c;
        matrixV *= c;

        return *this;
    }

    template<class OtherHandle>
    LMFModel &operator-=(const LMFModel<OtherHandle> &inOtherModel) {
        matrixU -= inOtherModel.matrixU;
        matrixV -= inOtherModel.matrixV;

        return *this;
    }

    template<class OtherHandle>
    LMFModel &operator+=(const LMFModel<OtherHandle> &inOtherModel) {
        matrixU += inOtherModel.matrixU;
        matrixV += inOtherModel.matrixV;

        return *this;
    }

    template<class OtherHandle>
    LMFModel &operator=(const LMFModel<OtherHandle> &inOtherModel) {
        matrixU = inOtherModel.matrixU;
        matrixV = inOtherModel.matrixV;

        return *this;
    }
};

typedef HandleTraits<MutableArrayHandle<double> >::ColumnVectorTransparentHandleMap
    GLMModel;

typedef HandleTraits<MutableArrayHandle<double> >::ColumnVectorTransparentHandleMap
    SVMModel;

// The necessity of this wrapper is to allow classes in algo/ and task/ to
// have a type that they can template over
template <class Handle>
struct MLPModel {
    typename HandleTraits<Handle>::ReferenceToDouble is_classification;
    typename HandleTraits<Handle>::ReferenceToDouble activation;
    typename HandleTraits<Handle>::ReferenceToDouble momentum;
    typename HandleTraits<Handle>::ReferenceToDouble is_nesterov;

    uint16_t num_layers;

    // std::vector<Eigen::Map<Matrix > > u;
    std::vector<MutableMappedMatrix> u;
    std::vector<MutableMappedMatrix> velocity;

    /**
     * @brief Space needed for the whole model
     *
     */
    static inline uint32_t arraySize(const uint16_t &inNumberOfStages,
                                     const double *inNumbersOfUnits) {
        // inNumberOfStages == 0 is not an expected value, but
        // it won't cause exception -- returning 0
        uint32_t size = 0;
        size_t N = inNumberOfStages;
        const double *n = inNumbersOfUnits;
        size_t k;
        for (k = 0; k < N; k ++) {
            size += static_cast<uint32_t>((n[k] + 1) * (n[k+1]));
        }
        //TODO conditionally assign size based on momentum
        return size * 2;     // position (u) + velocity
    }

    /**
     * @brief Space needed for the coefficients
     *
     */
    static inline uint32_t coeffArraySize(const uint16_t &inNumberOfStages,
                                          const double *inNumbersOfUnits) {
        // inNumberOfStages == 0 is not an expected value, but
        // it won't cause exception -- returning 0
        uint32_t size = 0;
        size_t N = inNumberOfStages;
        const double *n = inNumbersOfUnits;
        size_t k;
        for (k = 0; k < N; k ++) {
            size += (n[k] + 1) * (n[k+1]);
        }
        return size;     // weights (u)
    }

    size_t rebind(const double *is_classification_in,
                  const double *activation_in,
                  const double *momentum_in,
                  const double *is_nesterov_in,
                  const double *data,
                  const uint16_t &inNumberOfStages,
                  const double *inNumbersOfUnits) {
        const double *n = inNumbersOfUnits;
        size_t k;

        is_classification.rebind(is_classification_in);
        activation.rebind(activation_in);
        momentum.rebind(momentum_in);
        is_nesterov.rebind(is_nesterov_in);
        num_layers = inNumberOfStages;

        size_t sizeOfU = 0;
        u.clear();
        for (k = 0; k < num_layers; k ++) {
            u.push_back(MutableMappedMatrix());
            u[k].rebind(const_cast<double *>(data + sizeOfU),
                        static_cast<Index>(n[k] + 1),
                        static_cast<Index>(n[k+1]));
            sizeOfU += static_cast<size_t>((n[k] + 1) * (n[k+1]));
        }
        for (k = 0; k < num_layers; k ++) {
            velocity.push_back(MutableMappedMatrix());
            velocity[k].rebind(const_cast<double *>(data + sizeOfU),
                               n[k] + 1, n[k+1]);
            sizeOfU += (n[k] + 1) * (n[k+1]);
        }
        return sizeOfU;
    }

    void initialize(const uint16_t &inNumberOfStages,
                    const double *inNumbersOfUnits) {
        num_layers = inNumberOfStages;
        for (size_t k =0; k < num_layers; ++k){
            // Initalize according to Glorot and Bengio (2010)
            // See design doc for more info
            double span = 0.5 * sqrt(6.0 / (inNumbersOfUnits[k] + inNumbersOfUnits[k+1]));
            u[k] << span * Matrix::Random(u[k].rows(), u[k].cols());
            velocity[k].setZero();
        }
    }

    double norm() const {
        double norm = 0.;
        size_t k;
        for (k = 0; k < u.size(); k ++) {
            norm += u[k].bottomRows(u[k].rows()-1).squaredNorm();
        }
        return std::sqrt(norm);
    }

    void setZero(){
        size_t k;
        for (k = 0; k < u.size(); k ++) {
            u[k].setZero();
            velocity[k].setZero();
        }
    }

    /*
     *  Some operator wrappers for u.
     */
    MLPModel& operator*=(const double &c) {
        // Note that when scaling the model, don't update the bias.
        size_t k;
        for (k = 0; k < u.size(); k ++) {
           u[k] *= c;
        }

        return *this;
    }

    template<class OtherHandle>
    MLPModel& operator-=(const MLPModel<OtherHandle> &inOtherModel) {
        size_t k;
        for (k = 0; k < u.size() && k < inOtherModel.u.size(); k ++) {
            u[k] -= inOtherModel.u[k];
        }

        return *this;
    }

    template<class OtherHandle>
    MLPModel& operator+=(const MLPModel<OtherHandle> &inOtherModel) {
        size_t k;
        for (k = 0; k < u.size() && k < inOtherModel.u.size(); k ++) {
            u[k] += inOtherModel.u[k];
        }

        return *this;
    }

    template<class OtherHandle>
    MLPModel& operator=(const MLPModel<OtherHandle> &inOtherModel) {
        size_t k;
        for (k = 0; k < u.size() && k < inOtherModel.u.size(); k ++) {
            u[k] = inOtherModel.u[k];
            velocity[k] = inOtherModel.velocity[k];
        }
        num_layers = inOtherModel.num_layers;
        is_classification = inOtherModel.is_classification;
        activation = inOtherModel.activation;
        momentum = inOtherModel.momentum;
        is_nesterov = inOtherModel.is_nesterov;

        return *this;
    }
};

} // namespace convex

} // namespace modules

} // namespace madlib

#endif

