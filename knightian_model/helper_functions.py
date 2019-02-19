"""
Helper routines for solving the Knightian model.

"""

import numpy as np
from numba import njit, prange
from interpolation import interp


def initialize_values_and_policies(states_vals, b_vals):
    """
    Initializes arrays representing the value and policy functions.

    Parameters
    ----------
    states_vals : tuple
        Tuple of ndarray containing the approximation nodes for the state
        variables in the following order: w_vals, ζ_vals, ι_vals, k_tilde_vals.

    b_vals : ndarray(float, ndim=1)
        Array containing the approximation nodes for the borrowing choice
        variable.

    Returns
    ----------
    V1_star : ndarray(float, ndim=3)
        Initial guess of the first value function to be modified inplace with
        an approximate fixed point.

    V1_store : ndarray(float, ndim=3)
        Array used to store the previous guess of the first value function.

    V2_star : ndarray(float, ndim=3)
        Initial guess of the second value function to be modified inplace with
        an approximate fixed point.

    V2_store : ndarray(float, ndim=3)
        Array used to store the previous guess of the second value function.

    b_av : ndarray(float, ndim=4)
        Array used to store the action values of the different borrowing
        levels at the approximation nodes `b_vals`.

    k_tilde_av : ndarray(float, ndim=4)
        Array used to store the action values of the different net investment
        levels at the approximation nodes `k_tilde_vals`.

    """
    w_vals, ζ_vals, ι_vals, k_tilde_vals = states_vals

    # Initialize value functions
    V2_star = np.zeros((ζ_vals.size, k_tilde_vals.size, ι_vals.size))
    V2_store = np.zeros_like(V2_star)

    V1_star = np.zeros((ι_vals.size, ζ_vals.size, w_vals.size))
    V1_store = np.zeros_like(V1_star)

    # Initialize state action values
    b_av = np.zeros((ζ_vals.size, k_tilde_vals.size, b_vals.size, ι_vals.size))
    k_tilde_av = np.zeros((ι_vals.size, ζ_vals.size, w_vals.size,
                           k_tilde_vals.size))

    return V1_star, V1_store, V2_star, V2_store, b_av, k_tilde_av


def create_uc_grid(u, states_vals, wage, min_c=1e-20):
    """
    Create an array containing the value of the utility function `u` evaluated
    at grid points implied by `states_vals`.

    Parameters
    ----------
    u : callable
        The utility function to be evaluated.

    states_vals : tuple
        Tuple of ndarray containing the approximation nodes for the state
        variables in the following order: w_vals, ζ_vals, ι_vals, k_tilde_vals.

    wage : scalar(float)
        Wage earned from labor.

    min_c : scalar(float), optional(default=1e-20)
        Lower bound for clipping consumption values to avoid evaluating
        the utility function at negative consumption values.

    Returns
    ----------
    uc : ndarray(float, ndim=4)
        Array containing the utility function evaluations.

    """

    w_vals, ζ_vals, ι_vals, k_tilde_vals = states_vals

    uc = np.empty((ι_vals.size, ζ_vals.size, w_vals.size, k_tilde_vals.size))

    uc[:, :, :, :] = \
        w_vals[None, None, :, None] - k_tilde_vals[None, None, None, :]

    uc[0, :, :, :] += ζ_vals[:, None, None] * wage

    uc = u(np.maximum(uc, min_c))

    return uc


def create_next_w(r, δ_vals, k_tilde_vals, b_vals, R, Γ_star):
    """
    Create arrays for next wealth state variables using the law of motion for
    wealth.

    Parameters
    ----------
    r : scalar(float)
        Rate of return on the risky asset.

    δ_vals : ndarray(float, ndim=1)
        Possible values of δ.

    k_tilde_vals : ndarray(float, ndim=1)
        Approximation nodes for k_tilde.

    b_vals : ndarray(float, ndim=1)
        Approximation nodes for b.

    R : scalar(float)
        Rate of return on the risk-free asset.

    Γ_star : scalar(float)
        Return from a succesful invention.

    Returns
    ----------
    next_w : ndarray(float, ndim=3)
        Array containing the next period wealth values implied by the
        parameters without a succesful invention.

    next_w_star : ndarray(float, ndim=3)
        Array containing the next period wealth values implied by the
        parameters when an invention is succesful.

    """

    next_w = (1 + r) * δ_vals[:, None, None] * k_tilde_vals[None, :, None] + \
     (R - (1 + r) * δ_vals[:, None, None]) * b_vals[None, None, :]
    next_w_star = next_w + Γ_star

    return next_w, next_w_star


def create_P(P_δ, P_ζ, P_ι):
    """
    Combine `P_δ`, `P_ζ` and `P_ι` into a single matrix to be used in
    `solve_dp_vi`.

    Parameters
    ----------
    P_δ : ndarray(float, ndim=1)
        Probability distribution over the values of δ.

    P_ζ : ndarray(float, ndim=1)
        Probability distribution over the values of ζ.

    P_ι : ndarray(float, ndim=1)
        Probability distribution over the values of ι.

    Returns
    ----------
    P : ndarray(float, ndim=3)
        Joint probability distribution over the values of δ, ζ and ι.
        Probabilities vary by δ on the first axis, by ζ on the second axis,
        and by ι on the third axis.

    """

    P = \
        P_δ[:, None, None, None] * P_ζ[None, :, :, None] * \
        P_ι[None, None, None, :]

    return P