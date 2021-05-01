/* ----------------------------------------------------------------------- *//**
 *
 * @file igd.hpp
 *
 * Generic implementaion of incremental gradient descent, in the fashion of
 * user-definied aggregates. They should be called by actually database
 * functions, after arguments are properly parsed.
 *
 *//* ----------------------------------------------------------------------- */

#include <dbconnector/dbconnector.hpp>

#ifndef MADLIB_MODULES_CONVEX_ALGO_IGD_HPP_
#define MADLIB_MODULES_CONVEX_ALGO_IGD_HPP_

namespace madlib {

namespace modules {

namespace convex {

// use Eigen
using namespace madlib::dbal::eigen_integration;

// The reason for using ConstState instead of const State to reduce the
// template type list: flexibility to high-level for mutability control
// More: cast<ConstState>(MutableState) may not always work
template <class State, class ConstState, class Task>
class IGD {
public:
    typedef State state_type;
    typedef ConstState const_state_type;
    typedef typename Task::tuple_type tuple_type;
    typedef typename Task::model_type model_type;

    static void transition(state_type &state, const tuple_type &tuple);
    static void merge(state_type &state, const_state_type &otherState);
    static void transitionInMiniBatch(state_type &state, const tuple_type &tuple);
    static void transitionInMiniBatchWithALR(state_type &state, const tuple_type &tuple);
    static void mergeInPlace(state_type &state, const_state_type &otherState);
    static void final(state_type &state);
};

template <class State, class ConstState, class Task>
void
IGD<State, ConstState, Task>::transition(state_type &state,
        const tuple_type &tuple) {
    // The reason for update model inside a Task:: function instead of
    // returning the gradient and do it here: the gradient is a sparse
    // representation of the model (which is dense), returning the gradient
    // forces the algo to be aware of one more template type
    // -- Task::sparse_model_type, which we do not explicit define

    // apply to the model directly
    Task::gradientInPlace(
            state.algo.incrModel,
            tuple.indVar,
            tuple.depVar,
            state.task.stepsize * tuple.weight);
}

template <class State, class ConstState, class Task>
void
IGD<State, ConstState, Task>::merge(state_type &state,
        const_state_type &otherState) {
    // Having zero checking here to reduce dependency to the caller.
    // This can be removed if it affects performance in the future,
    // with the expectation that callers should do the zero checking.
    if (state.algo.numRows == 0) {
        state.algo.incrModel = otherState.algo.incrModel;
        return;
    } else if (otherState.algo.numRows == 0) {
        return;
    }

    // The reason of this weird algorithm instead of an intuitive one
    // -- (w1 * m1 + w2 * m2) / (w1 + w2): we have only one mutable state,
    // therefore, (m1 * w1 / w2  + m2)  * w2 / (w1 + w2).
    // Order:         111111111  22222  3333333333333333

    // model averaging, weighted by rows seen
    double totalNumRows = static_cast<double>(state.algo.numRows + otherState.algo.numRows);
    state.algo.incrModel *= static_cast<double>(state.algo.numRows) /
        static_cast<double>(otherState.algo.numRows);
    state.algo.incrModel += otherState.algo.incrModel;
    state.algo.incrModel *= static_cast<double>(otherState.algo.numRows) /
        static_cast<double>(totalNumRows);
}

/**
  * @brief Update the transition state in mini-batches
  *
  * Note: We assume that
  *     1. Task defines a model_eigen_type
  *     2. A batch of tuple.indVar is a Matrix
  *     3. A batch of tuple.depVar is a ColumnVector
  *     4. Task defines a getLossAndUpdateModel method
  *
 */
 template <class State, class ConstState, class Task>
 void
 IGD<State, ConstState, Task>::transitionInMiniBatch(
        state_type &state,
        const tuple_type &tuple) {

    madlib_assert(tuple.indVar.rows() == tuple.depVar.rows(),
                  std::runtime_error("Invalid data. Independent and dependent "
                                     "batches don't have same number of rows."));

    uint16_t batch_size = state.batchSize;
    uint16_t n_epochs = state.nEpochs;

    // n_rows/n_ind_cols are the rows/cols in a transition tuple.
    Index n_rows = tuple.indVar.rows();
    size_t n_batches = n_rows < batch_size ? 1 :
                        size_t(n_rows / batch_size) + size_t(n_rows % batch_size > 0);

    double max_loss = 0.0;
    for (int curr_epoch=0; curr_epoch < n_epochs; curr_epoch++) {
        double loss = 0.0;
        /*
            Randomizing the input data before every iteration is good for
            minibatch gradient descent convergence. Since we don't do that,
            we are randomizing the order in which every batch is visited in
            a buffer. Note that this still does not randomize rows within
            a batch.
        */
        std::vector<size_t> random_curr_batch(n_batches, 0);
        for(size_t i=0; i < n_batches; i++) {
            random_curr_batch[i] = i;
        }
        std::random_shuffle(&random_curr_batch[0], &random_curr_batch[n_batches]);

        for (size_t i = 0; i < n_batches; i++) {
            size_t curr_batch = random_curr_batch[i];
            Index curr_batch_row_index = static_cast<Index>(curr_batch * batch_size);
            Matrix X_batch;
            Matrix Y_batch;
            if (curr_batch == n_batches-1) {
               // last batch
               X_batch = tuple.indVar.bottomRows(n_rows - curr_batch_row_index);
               Y_batch = tuple.depVar.bottomRows(n_rows - curr_batch_row_index);
            } else {
                X_batch = tuple.indVar.block(curr_batch_row_index, 0,
                                             batch_size, tuple.indVar.cols());
                Y_batch = tuple.depVar.block(curr_batch_row_index, 0,
                                             batch_size, tuple.depVar.cols());
            }
            Task::lambda = state.lambda;
            loss += Task::getLossAndUpdateModel(
                state.model, X_batch, Y_batch, state.stepsize);
        }

        if (max_loss < loss) max_loss = loss;
    }
    // Be pessimistic and report the maximum loss
    state.loss += max_loss;
    return;
 }

/**
  * @brief Update the transition state in mini-batches using adaptive learning
  *        rate solvers.
  *
  * Note: We assume that
  *     1. Task defines a model_eigen_type
  *     2. A batch of tuple.indVar is a Matrix
  *     3. A batch of tuple.depVar is a ColumnVector
  *     4. Task defines a getLossAndUpdateModel method
  *
 */
 template <class State, class ConstState, class Task>
 void
 IGD<State, ConstState, Task>::transitionInMiniBatchWithALR(
        state_type &state,
        const tuple_type &tuple) {

    madlib_assert(tuple.indVar.rows() == tuple.depVar.rows(),
                  std::runtime_error("Invalid data. Independent and dependent "
                                     "batches don't have same number of rows."));

    uint16_t batch_size = state.batchSize;
    uint16_t n_epochs = state.nEpochs;

    // n_rows/n_ind_cols are the rows/cols in a transition tuple.
    Index n_rows = tuple.indVar.rows();
    size_t n_batches = n_rows < batch_size ? 1 :
                        size_t(n_rows / batch_size) + size_t(n_rows % batch_size > 0);

    double max_loss = 0.0;
    std::vector<Matrix> m(state.model.num_layers);
    std::vector<Matrix> v(state.model.num_layers);
    int t = 0;
    for (Index k=0; k < state.model.num_layers; ++k) {
        m[k] = Matrix::Zero(state.model.u[k].rows(), state.model.u[k].cols());
        v[k] = Matrix::Zero(state.model.u[k].rows(), state.model.u[k].cols());
    }
    for (int curr_epoch=0; curr_epoch < n_epochs; curr_epoch++) {
        double loss = 0.0;
        /*
            Randomizing the input data before every iteration is good for
            minibatch gradient descent convergence. Since we don't do that,
            we are randomizing the order in which every batch is visited in
            a buffer. Note that this still does not randomize rows within
            a batch.
        */
        std::vector<size_t> random_curr_batch(n_batches, 0);
        for(size_t i=0; i < n_batches; i++) {
            random_curr_batch[i] = i;
        }
        std::random_shuffle(&random_curr_batch[0], &random_curr_batch[n_batches]);

        for (size_t i = 0; i < n_batches; i++) {
            size_t curr_batch = random_curr_batch[i];
            Index curr_batch_row_index = static_cast<Index>(curr_batch * batch_size);
            Matrix X_batch;
            Matrix Y_batch;
            if (curr_batch == n_batches-1) {
               // last batch
               X_batch = tuple.indVar.bottomRows(n_rows - curr_batch_row_index);
               Y_batch = tuple.depVar.bottomRows(n_rows - curr_batch_row_index);
            } else {
                X_batch = tuple.indVar.block(curr_batch_row_index, 0,
                                             batch_size, tuple.indVar.cols());
                Y_batch = tuple.depVar.block(curr_batch_row_index, 0,
                                             batch_size, tuple.depVar.cols());
            }
            t++;
            Task::lambda = state.lambda;
            loss += Task::getLossAndUpdateModelALR(state.model, X_batch, Y_batch,
                                                state.stepsize, state.opt_code,
                                                state.rho, m, state.beta1,
                                                state.beta2, v, t, state.eps);
        }

        if (max_loss < loss) max_loss = loss;
    }
    // Be pessimistic and report the maximum loss
    state.loss += max_loss;
    return;
 }


template <class State, class ConstState, class Task>
void
IGD<State, ConstState, Task>::mergeInPlace(state_type &state,
        const_state_type &otherState) {
    // avoid division by zero
    if (state.numRows == 0) {
        state.model = otherState.model;
        return;
    } else if (otherState.numRows == 0) {
        return;
    }

    // model averaging, weighted by rows seen
    double leftRows = static_cast<double>(state.numRows + state.numRows);
    double rightRows = static_cast<double>(otherState.numRows + otherState.numRows);
    double totalNumRows = leftRows + rightRows;
    state.model *= leftRows / rightRows;
    state.model += otherState.model;
    state.model *= rightRows / totalNumRows;
}

template <class State, class ConstState, class Task>
void
IGD<State, ConstState, Task>::final(state_type &state) {
    // The reason that we have to keep the task.model untouched in transition
    // funtion: loss computation needs the model from last iteration cleanly
    state.task.model = state.algo.incrModel;

}

} // namespace convex

} // namespace modules

} // namespace madlib

#endif

