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
            int numberOfStages = numbersOfUnits.size() - 1;

            double stepsize = args[5].getAs<double>();
            state.allocate(*this, numberOfStages,
                           reinterpret_cast<const double *>(numbersOfUnits.ptr()));
            state.task.stepsize = stepsize;

            const int activation = args[6].getAs<int>();
            const int is_classification = args[7].getAs<int>();
            // args[8] is for weighting the input row, which is populated later.
            const bool warm_start = args[9].getAs<bool>();
            const double lambda = args[11].getAs<double>();
            state.task.lambda = lambda;
            MLPTask::lambda = lambda;

            double is_classification_double = (double) is_classification;
            double activation_double = (double) activation;
            MappedColumnVector coeff = args[10].getAs<MappedColumnVector>();
            state.task.model.rebind(&is_classification_double,&activation_double,
                                    &coeff.data()[0], numberOfStages,
                                    &numbersOfUnits[0]);

            // state.task.model.is_classification =
            //     static_cast<double>(is_classification);
            // state.task.model.activation = static_cast<double>(activation);
            // MappedColumnVector initial_coeff = args[10].getAs<MappedColumnVector>();
            // // copy initial_coeff into the model
            // Index fan_in, fan_out, layer_start = 0;
            // for (size_t k = 0; k < numberOfStages; ++k){
            //     fan_in = numbersOfUnits[k];
            //     fan_out = numbersOfUnits[k+1];
            //     state.task.model.u[k] << initial_coeff.segment(layer_start, (fan_in+1)*fan_out);
            //     layer_start = (fan_in + 1) * fan_out;
            // }
        }
        // resetting in either case
        state.reset();
    }

    // tuple
    ColumnVector indVar;
    MappedColumnVector depVar;
    try {
        indVar = args[1].getAs<MappedColumnVector>();
        MappedColumnVector y = args[2].getAs<MappedColumnVector>();
        depVar.rebind(y.memoryHandle(), y.size());
    } catch (const ArrayWithNullException &e) {
        return args[0];
    }
    MLPTuple tuple;
    tuple.indVar = indVar;
    tuple.depVar.rebind(depVar.memoryHandle(), depVar.size());
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

    // initilize the state if first tuple
    if (state.algo.numRows == 0) {
        if (!args[3].isNull()) {
            MLPMiniBatchState<ArrayHandle<double> > previousState = args[3];
            state.allocate(*this, previousState.task.numberOfStages,
                           previousState.task.numbersOfUnits);
            state = previousState;
        } else {
            // configuration parameters
            ArrayHandle<double> numbersOfUnits = args[4].getAs<ArrayHandle<double> >();
            int numberOfStages = numbersOfUnits.size() - 1;

            double stepsize = args[5].getAs<double>();

            state.allocate(*this, numberOfStages,
                           reinterpret_cast<const double *>(numbersOfUnits.ptr()));
            state.task.stepsize = stepsize;
            const int activation = args[6].getAs<int>();
            const int is_classification = args[7].getAs<int>();
            // args[8] is for weighting the input row, which is populated later.
            const bool warm_start = args[9].getAs<bool>();
            const double lambda = args[11].getAs<double>();
            state.algo.batchSize = args[12].getAs<int>();
            state.algo.nEpochs = args[13].getAs<int>();
            state.task.lambda = lambda;
            MLPTask::lambda = lambda;

            /* FIXME: The state is set back to zero for second row onwards if
               initialized as in IGD. The following avoids that, but there is
               some failure with debug build that must be fixed.
            */
            state.task.model.is_classification =
                static_cast<double>(is_classification);
            state.task.model.activation = static_cast<double>(activation);
            MappedColumnVector initial_coeff = args[10].getAs<MappedColumnVector>();
            // copy initial_coeff into the model
            Index fan_in, fan_out, layer_start = 0;
            for (size_t k = 0; k < numberOfStages; ++k){
                fan_in = numbersOfUnits[k];
                fan_out = numbersOfUnits[k+1];
                state.task.model.u[k] << initial_coeff.segment(layer_start, (fan_in+1)*fan_out);
                layer_start = (fan_in + 1) * fan_out;
            }
        }
        // resetting in either case
        state.reset();
    }

    // tuple
    Matrix indVar;
    Matrix depVar;
    try {
        // Ideally there should be no NULLs in the pre-processed input data,
        // but keep it in a try block in case the user has modified the
        // pre-processed data in any way.
        indVar = args[1].getAs<MappedMatrix>();
        depVar = args[2].getAs<MappedMatrix>();
    } catch (const ArrayWithNullException &e) {
        return args[0];
    }
    MiniBatchTuple tuple;
    // The matrices are by default read as column-major. We will have to
    // transpose it to get back the matrix like how it is in the database.
    tuple.indVar = trans(indVar);
    tuple.depVar = trans(depVar);
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
    state.algo.numRows += tuple.indVar.rows();
    return state;
}

/**
 * @brief Perform the perliminary aggregation function: Merge transition states
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
 * @brief Perform the perliminary aggregation function: Merge transition states
 */
AnyType
mlp_minibatch_merge::run(AnyType &args) {
    MLPMiniBatchState<MutableArrayHandle<double> > stateLeft = args[0];
    MLPMiniBatchState<ArrayHandle<double> > stateRight = args[1];

    if (stateLeft.algo.numRows == 0) { return stateRight; }
    else if (stateRight.algo.numRows == 0) { return stateLeft; }

    MLPMiniBatchAlgorithm::mergeInPlace(stateLeft, stateRight);

    // The following numRows update, cannot be put above, because the model
    // averaging depends on their original values
    stateLeft.algo.numRows += stateRight.algo.numRows;
    stateLeft.algo.loss += stateRight.algo.loss;

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
 * @brief Perform the multilayer perceptron final step
 */
AnyType
mlp_minibatch_final::run(AnyType &args) {
    // We request a mutable object. Depending on the backend, this might perform
    // a deep copy.
    MLPMiniBatchState<MutableArrayHandle<double> > state = args[0];
    // Aggregates that haven't seen any data just return Null.
    if (state.algo.numRows == 0) { return Null(); }

    L2<MLPModelType>::lambda = state.task.lambda;
    state.algo.loss = state.algo.loss/static_cast<double>(state.algo.numRows);
    state.algo.loss += L2<MLPModelType>::loss(state.task.model);
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

    return std::abs(stateLeft.algo.loss - stateRight.algo.loss);
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
                    state.task.model.arraySize(state.task.numberOfStages,
                                               state.task.numbersOfUnits));
    double loss = state.algo.loss;

    AnyType tuple;
    tuple << flattenU
          << loss;
    return tuple;
}

/**
 * @brief Return the coefficients and diagnostic statistics of the state
 */
AnyType
internal_mlp_minibatch_result::run(AnyType &args) {
    MLPMiniBatchState<ArrayHandle<double> > state = args[0];
    HandleTraits<ArrayHandle<double> >::ColumnVectorTransparentHandleMap flattenU;
    flattenU.rebind(&state.task.model.u[0](0, 0),
                    state.task.model.arraySize(state.task.numberOfStages,
                                               state.task.numbersOfUnits));
    double loss = state.algo.loss;

    AnyType tuple;
    tuple << flattenU
          << loss;
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
    size_t numberOfStages = layerSizes.size()-1;
    double is_classification = args[2].getAs<double>();
    double activation = args[3].getAs<double>();
    int is_dep_var_array_for_classification = args[8].getAs<int>();
    bool is_classification_response = is_classification && is_response;

    model.rebind(&is_classification, &activation, &coeff.data()[0],
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

