/*
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
 * @file mlp_igd.cpp
 *
 * @brief Multilayer Perceptron functions
 *
 *//* ----------------------------------------------------------------------- */
#include <boost/lexical_cast.hpp>

#include <dbconnector/dbconnector.hpp>
#include <modules/shared/HandleTraits.hpp>

#include "mlp_igd.hpp"

#include "task/mlp.hpp"
#include "task/l2.hpp"
#include "algo/igd.hpp"
#include "algo/loss.hpp"

#include "type/tuple.hpp"
#include "type/model.hpp"
#include "type/state.hpp"

namespace madlib {

namespace modules {

namespace convex {

// These 2 classes contain public static methods that can be called
typedef IGD<MLPIGDState<MutableArrayHandle<double> >, MLPIGDState<ArrayHandle<double> >,
        MLP<MLPModel<MutableArrayHandle<double> >, MLPTuple > > MLPIGDAlgorithm;

typedef IGD<MLPMiniBatchState<MutableArrayHandle<double> >, MLPMiniBatchState<ArrayHandle<double> >,
        MLP<MLPModel<MutableArrayHandle<double> >, MiniBatchTuple > > MLPMiniBatchAlgorithm;

typedef IGD<MLPALRState<MutableArrayHandle<double> >, MLPALRState<ArrayHandle<double> >,
        MLP<MLPModel<MutableArrayHandle<double> >, MiniBatchTuple > > MLPALRAlgorithm;

typedef Loss<MLPIGDState<MutableArrayHandle<double> >, MLPIGDState<ArrayHandle<double> >,
        MLP<MLPModel<MutableArrayHandle<double> >, MLPTuple > > MLPLossAlgorithm;

typedef MLP<MLPModel<MutableArrayHandle<double> >,MLPTuple> MLPTask;

typedef MLPModel<MutableArrayHandle<double> > MLPModelType;

/**
 * @brief Perform the multilayer perceptron transition step
 *
 * Called for each tuple.
 */
AnyType
mlp_igd_transition::run(AnyType &args) {
    // For the first tuple: args[0] is nothing more than a marker that
    // indicates that we should do some initial operations.
    // For other tuples: args[0] holds the computation state until last tuple
    MLPIGDState<MutableArrayHandle<double> > state = args[0];

    // initilize the state if first tuple
    if (state.algo.numRows == 0) {
        if (!args[3].isNull()) {
            MLPIGDState<ArrayHandle<double> > previousState = args[3];

            state.allocate(*this, previousState.task.numberOfStages,
                           previousState.task.numbersOfUnits);
            state = previousState;
        } else {
            // configuration parameters and initialization
            // this is run only once (first iteration, first tuple)
            ArrayHandle<double> numbersOfUnits = args[4].getAs<ArrayHandle<double> >();
            uint16_t numberOfStages = static_cast<uint16_t>(numbersOfUnits.size() - 1);

            state.allocate(*this, numberOfStages,
                           reinterpret_cast<const double *>(numbersOfUnits.ptr()));
            state.task.stepsize = args[5].getAs<double>();
            state.task.model.activation = static_cast<double>(args[6].getAs<int>());
            state.task.model.is_classification = static_cast<double>(args[7].getAs<int>());
            // args[8] is for weighting the input row, which is populated later.
            state.task.lambda = args[10].getAs<double>();
            MLPTask::lambda = state.task.lambda;
            state.task.model.momentum = args[11].getAs<double>();
            state.task.model.is_nesterov = static_cast<double>(args[12].getAs<bool>());
            if (!args[9].isNull()){
                // initial coefficients are provided
                MappedColumnVector warm_start_coeff = args[9].getAs<MappedColumnVector>();

                // copy warm start into the task model
                // state.reset() ensures algo.incrModel is copied from task.model
                Index layer_start = 0;
                for (size_t k = 0; k < numberOfStages; ++k){
                    for (Index j=0; j < state.task.model.u[k].cols(); ++j){
                        for (Index i=0; i < state.task.model.u[k].rows(); ++i){
                            state.task.model.u[k](i, j) = warm_start_coeff(
                                layer_start + j * state.task.model.u[k].rows() + i);
                        }
                    }
                    layer_start += state.task.model.u[k].rows() * state.task.model.u[k].cols();
                }
            } else {
                // initialize the model with appropriate coefficients
                state.task.model.initialize(
                    numberOfStages,
                    reinterpret_cast<const double *>(numbersOfUnits.ptr()));
            }
        }
        // resetting in either case
        state.reset();
    }

    MLPTuple tuple;
    try {
        tuple.indVar = args[1].getAs<MappedColumnVector>();;
        tuple.depVar = args[2].getAs<MappedColumnVector>();
    } catch (const ArrayWithNullException &e) {
        return args[0];
    }

    tuple.weight = args[8].getAs<double>();
    MLPIGDAlgorithm::transition(state, tuple);
    // Use the model from the previous iteration to compute the loss (note that
    // it is stored in Task's state, and the Algo's state holds the model from
    // the current iteration.
    MLPLossAlgorithm::transition(state, tuple);
    state.algo.numRows ++;

    return state;
}

/**
 * @brief Perform the preliminary aggregation function: Merge transition states
 */
AnyType
mlp_igd_merge::run(AnyType &args) {
    MLPIGDState<MutableArrayHandle<double> > stateLeft = args[0];
    MLPIGDState<ArrayHandle<double> > stateRight = args[1];

    if (stateLeft.algo.numRows == 0) { return stateRight; }
    else if (stateRight.algo.numRows == 0) { return stateLeft; }

    MLPIGDAlgorithm::merge(stateLeft, stateRight);
    MLPLossAlgorithm::merge(stateLeft, stateRight);

    // The following numRows update cannot be put above, because the model
    // averaging depends on their original values
    stateLeft.algo.numRows += stateRight.algo.numRows;

    return stateLeft;
}
/**
 * @brief Perform the multilayer perceptron final step
 */
AnyType
mlp_igd_final::run(AnyType &args) {
    // We request a mutable object. Depending on the backend, this might perform
    // a deep copy.
    MLPIGDState<MutableArrayHandle<double> > state = args[0];

    if (state.algo.numRows == 0) { return Null(); }

    L2<MLPModelType>::lambda = state.task.lambda;
    state.algo.loss = state.algo.loss/static_cast<double>(state.algo.numRows);
    state.algo.loss += L2<MLPModelType>::loss(state.task.model);
    MLPIGDAlgorithm::final(state);
    return state;
}

/**
 * @brief Perform the multilayer perceptron minibatch transition step
 *
 * Called for each tuple.
 */
AnyType
mlp_minibatch_transition::run(AnyType &args) {
    // For the first tuple: args[0] is nothing more than a marker that
    // indicates that we should do some initial operations.
    // For other tuples: args[0] holds the computation state until last tuple

    MLPMiniBatchState<MutableArrayHandle<double> > state = args[0];

    // initialize the state if first tuple
    if (state.numRows == 0) {
        if (!args[3].isNull()) {
            MLPMiniBatchState<ArrayHandle<double> > previousState = args[3];
            state.allocate(*this, previousState.numberOfStages,
                           previousState.numbersOfUnits);
            state = previousState;
        } else {
            // configuration parameters
            ArrayHandle<double> numbersOfUnits = args[4].getAs<ArrayHandle<double> >();
            uint16_t numberOfStages = static_cast<uint16_t>(numbersOfUnits.size() - 1);
            state.allocate(*this, numberOfStages,
                           reinterpret_cast<const double *>(numbersOfUnits.ptr()));
            state.stepsize = args[5].getAs<double>();
            state.model.activation = static_cast<double>(args[6].getAs<int>());
            state.model.is_classification = static_cast<double>(args[7].getAs<int>());
            // args[8] is for weighting the input row, which is populated later.
            state.model.momentum = args[13].getAs<double>();
            state.model.is_nesterov = static_cast<double>(args[14].getAs<bool>());
            if (!args[9].isNull()){
                // initial coefficients are provided copy warm start into the model
                MappedColumnVector warm_start_coeff = args[9].getAs<MappedColumnVector>();
                Index layer_start = 0;
                for (size_t k = 0; k < numberOfStages; ++k){
                    for (Index j=0; j < state.model.u[k].cols(); ++j){
                        for (Index i=0; i < state.model.u[k].rows(); ++i){
                            state.model.u[k](i, j) = warm_start_coeff(
                                layer_start + j * state.model.u[k].rows() + i);
                        }
                    }
                    layer_start += state.model.u[k].rows() * state.model.u[k].cols();
                }
            } else {
                // initialize the model with appropriate coefficients
                state.model.initialize(
                    numberOfStages,
                    reinterpret_cast<const double *>(numbersOfUnits.ptr()));
            }

            state.lambda = args[10].getAs<double>();
            MLPTask::lambda = state.lambda;
            state.batchSize = static_cast<uint16_t>(args[11].getAs<int>());
            state.nEpochs = static_cast<uint16_t>(args[12].getAs<int>());
        }
        // resetting in either case
        state.reset();
    }

    MiniBatchTuple tuple;
    try {
        // Ideally there should be no NULLs in the pre-processed input data,
        // but keep it in a try block in case the user has modified the
        // pre-processed data in any way.
        // The matrices are by default read as column-major. We will have to
        // transpose it to get back the matrix like how it is in the database.
        tuple.indVar = trans(args[1].getAs<MappedMatrix>());
        tuple.depVar = trans(args[2].getAs<MappedMatrix>());
    } catch (const ArrayWithNullException &e) {
        return args[0];
    }

    tuple.weight = args[8].getAs<double>();

    /*
        Note that the IGD version uses the model in Task (model from the
        previous iteration) to compute the loss.
        Minibatch uses the model from Algo (the model based on current
        iteration) to compute the loss. The difference in loss based on one
        iteration is not too much, hence doing so here. We therefore don't
        need to maintain another copy of the model (from previous iteration)
        in the state. The model for the current iteration, and the loss are
        both computed in one function now.
    */
    MLPMiniBatchAlgorithm::transitionInMiniBatch(state, tuple);
    state.numRows += tuple.indVar.rows();
    return state;
}
/**
 * @brief Perform the perliminary aggregation function: Merge transition states
 */
AnyType
mlp_minibatch_merge::run(AnyType &args) {
    MLPMiniBatchState<MutableArrayHandle<double> > stateLeft = args[0];
    MLPMiniBatchState<ArrayHandle<double> > stateRight = args[1];

    if (stateLeft.numRows == 0) { return stateRight; }
    else if (stateRight.numRows == 0) { return stateLeft; }

    MLPMiniBatchAlgorithm::mergeInPlace(stateLeft, stateRight);

    // The following numRows update, cannot be put above, because the model
    // averaging depends on their original values
    stateLeft.numRows += stateRight.numRows;
    stateLeft.loss += stateRight.loss;

    return stateLeft;
}

/**
 * @brief Perform the multilayer perceptron final step
 */
AnyType
mlp_minibatch_final::run(AnyType &args) {
    // We request a mutable object. Depending on the backend, this might perform
    // a deep copy.
    MLPMiniBatchState<MutableArrayHandle<double> > state = args[0];
    // Aggregates that haven't seen any data just return Null.
    if (state.numRows == 0) { return Null(); }

    L2<MLPModelType>::lambda = state.lambda;
    state.loss = state.loss/static_cast<double>(state.numRows);
    state.loss += L2<MLPModelType>::loss(state.model);
    return state;
}

/**
 * @brief Perform the multilayer perceptron minibatch transition step
 *
 * Called for each tuple.
 */
AnyType
mlp_alr_transition::run(AnyType &args) {
    // For the first tuple: args[0] is nothing more than a marker that
    // indicates that we should do some initial operations.
    // For other tuples: args[0] holds the computation state until last tuple

    MLPALRState<MutableArrayHandle<double> > state = args[0];

    // initialize the state if first tuple
    if (state.numRows == 0) {
        if (!args[3].isNull()) {
            MLPALRState<ArrayHandle<double> > previousState = args[3];
            state.allocate(*this, previousState.numberOfStages,
                           previousState.numbersOfUnits);
            state = previousState;
        } else {
            // configuration parameters
            ArrayHandle<double> numbersOfUnits = args[4].getAs<ArrayHandle<double> >();
            uint16_t numberOfStages = static_cast<uint16_t>(numbersOfUnits.size() - 1);
            state.allocate(*this, numberOfStages,
                           reinterpret_cast<const double *>(numbersOfUnits.ptr()));
            state.stepsize = args[5].getAs<double>();
            state.model.activation = static_cast<double>(args[6].getAs<int>());
            state.model.is_classification = static_cast<double>(args[7].getAs<int>());
            // args[8] is for weighting the input row, which is populated later.
            if (!args[9].isNull()){
                // initial coefficients are provided copy warm start into the model
                MappedColumnVector warm_start_coeff = args[9].getAs<MappedColumnVector>();
                Index layer_start = 0;
                for (size_t k = 0; k < numberOfStages; ++k){
                    for (Index j=0; j < state.model.u[k].cols(); ++j){
                        for (Index i=0; i < state.model.u[k].rows(); ++i){
                            state.model.u[k](i, j) = warm_start_coeff(
                                layer_start + j * state.model.u[k].rows() + i);
                        }
                    }
                    layer_start += state.model.u[k].rows() * state.model.u[k].cols();
                }
            } else {
                // initialize the model with appropriate coefficients
                state.model.initialize(
                    numberOfStages,
                    reinterpret_cast<const double *>(numbersOfUnits.ptr()));
            }

            state.lambda = args[10].getAs<double>();
            MLPTask::lambda = state.lambda;
            state.batchSize = static_cast<uint16_t>(args[11].getAs<int>());
            state.nEpochs = static_cast<uint16_t>(args[12].getAs<int>());
            state.opt_code = static_cast<uint16_t>(args[13].getAs<int>());
            state.rho = args[14].getAs<double>();
            state.beta1 = args[15].getAs<double>();
            state.beta2 = args[16].getAs<double>();
            state.eps = args[17].getAs<double>();
        }
        // resetting in either case
        state.reset();
    }

    MiniBatchTuple tuple;
    try {
        // Ideally there should be no NULLs in the pre-processed input data,
        // but keep it in a try block in case the user has modified the
        // pre-processed data in any way.
        // The matrices are by default read as column-major. We will have to
        // transpose it to get back the matrix like how it is in the database.
        tuple.indVar = trans(args[1].getAs<MappedMatrix>());
        tuple.depVar = trans(args[2].getAs<MappedMatrix>());
    } catch (const ArrayWithNullException &e) {
        return args[0];
    }

    tuple.weight = args[8].getAs<double>();

    /*
        Note that the IGD version uses the model in Task (model from the
        previous iteration) to compute the loss.
        Minibatch uses the model from Algo (the model based on current
        iteration) to compute the loss. The difference in loss based on one
        iteration is not too much, hence doing so here. We therefore don't
        need to maintain another copy of the model (from previous iteration)
        in the state. The model for the current iteration, and the loss are
        both computed in one function now.
    */
    MLPALRAlgorithm::transitionInMiniBatchWithALR(state, tuple);
    state.numRows += tuple.indVar.rows();
    return state;
}
/**
 * @brief Perform the perliminary aggregation function: Merge transition states
 */
AnyType
mlp_alr_merge::run(AnyType &args) {
    MLPALRState<MutableArrayHandle<double> > stateLeft = args[0];
    MLPALRState<ArrayHandle<double> > stateRight = args[1];

    if (stateLeft.numRows == 0) { return stateRight; }
    else if (stateRight.numRows == 0) { return stateLeft; }

    MLPALRAlgorithm::mergeInPlace(stateLeft, stateRight);

    // The following numRows update, cannot be put above, because the model
    // averaging depends on their original values
    stateLeft.numRows += stateRight.numRows;
    stateLeft.loss += stateRight.loss;

    return stateLeft;
}

/**
 * @brief Perform the multilayer perceptron final step
 */
AnyType
mlp_alr_final::run(AnyType &args) {
    // We request a mutable object. Depending on the backend, this might perform
    // a deep copy.
    MLPALRState<MutableArrayHandle<double> > state = args[0];
    // Aggregates that haven't seen any data just return Null.
    if (state.numRows == 0) { return Null(); }

    L2<MLPModelType>::lambda = state.lambda;
    state.loss = state.loss/static_cast<double>(state.numRows);
    state.loss += L2<MLPModelType>::loss(state.model);
    return state;
}

/**
 * @brief Return the difference in RMSE between two states
 */
AnyType
internal_mlp_igd_distance::run(AnyType &args) {
    MLPIGDState<ArrayHandle<double> > stateLeft = args[0];
    MLPIGDState<ArrayHandle<double> > stateRight = args[1];
    return std::abs(stateLeft.algo.loss - stateRight.algo.loss);
}


AnyType
internal_mlp_minibatch_distance::run(AnyType &args) {
    MLPMiniBatchState<ArrayHandle<double> > stateLeft = args[0];
    MLPMiniBatchState<ArrayHandle<double> > stateRight = args[1];

    return std::abs(stateLeft.loss - stateRight.loss);
}

AnyType
internal_mlp_alr_distance::run(AnyType &args) {
    MLPALRState<ArrayHandle<double> > stateLeft = args[0];
    MLPALRState<ArrayHandle<double> > stateRight = args[1];

    return std::abs(stateLeft.loss - stateRight.loss);
}

/**
 * @brief Return the coefficients and diagnostic statistics of the state
 */
AnyType
internal_mlp_igd_result::run(AnyType &args) {
    MLPIGDState<ArrayHandle<double> > state = args[0];
    HandleTraits<ArrayHandle<double> >::ColumnVectorTransparentHandleMap
        flattenU;
    flattenU.rebind(&state.task.model.u[0](0, 0),
                    state.task.model.coeffArraySize(state.task.numberOfStages,
                                               state.task.numbersOfUnits));
    AnyType tuple;
    tuple << flattenU
          << static_cast<double>(state.algo.loss);;
    return tuple;
}

/**
 * @brief Return the coefficients and diagnostic statistics of the state
 */
AnyType
internal_mlp_minibatch_result::run(AnyType &args) {
    MLPMiniBatchState<ArrayHandle<double> > state = args[0];
    HandleTraits<ArrayHandle<double> >::ColumnVectorTransparentHandleMap flattenU;
    flattenU.rebind(&state.model.u[0](0, 0),
                    state.model.coeffArraySize(state.numberOfStages,
                                          state.numbersOfUnits));
    AnyType tuple;
    tuple << flattenU
          << static_cast<double>(state.loss);
    return tuple;
}

/**
 * @brief Return the coefficients and diagnostic statistics of the state
 */
AnyType
internal_mlp_alr_result::run(AnyType &args) {
    MLPALRState<ArrayHandle<double> > state = args[0];
    HandleTraits<ArrayHandle<double> >::ColumnVectorTransparentHandleMap flattenU;
    flattenU.rebind(&state.model.u[0](0, 0),
                    state.model.coeffArraySize(state.numberOfStages,
                                          state.numbersOfUnits));
    AnyType tuple;
    tuple << flattenU
          << static_cast<double>(state.loss);
    return tuple;
}

AnyType
internal_predict_mlp::run(AnyType &args) {
    MLPModel<MutableArrayHandle<double> > model;
    ColumnVector indVar;
    int is_response = args[5].getAs<int>();
    MappedColumnVector x_means = args[6].getAs<MappedColumnVector>();
    MappedColumnVector x_stds = args[7].getAs<MappedColumnVector>();
    MappedColumnVector coeff = args[0].getAs<MappedColumnVector>();
    MappedColumnVector layerSizes = args[4].getAs<MappedColumnVector>();
    // Input layer doesn't count
    uint16_t numberOfStages = static_cast<uint16_t>(layerSizes.size() - 1);
    double is_classification = args[2].getAs<double>();
    double activation = args[3].getAs<double>();
    int is_dep_var_array_for_classification = args[8].getAs<int>();
    bool is_classification_response = is_classification && is_response;

    // The model rebind function is called by both predict and train functions.
    // Since we have to use the same function, we are passing a dummy value for
    // activation, momentum and nesterov because predict does not care
    // about the actual values for these params.
    const double dummy_value = static_cast<double>(-1);
    model.rebind(&is_classification, &activation, &dummy_value, &dummy_value, &coeff.data()[0],
                 numberOfStages, &layerSizes.data()[0]);
    try {
        indVar = (args[1].getAs<MappedColumnVector>()-x_means).cwiseQuotient(x_stds);
    } catch (const ArrayWithNullException &e) {
        return args[0];
    }
    ColumnVector prediction = MLPTask::predict(model, indVar, is_classification_response,
                                               is_dep_var_array_for_classification);
    return prediction;
}


} // namespace convex

} // namespace modules

} // namespace madlib

