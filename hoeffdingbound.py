import math


def variance(count, n):
    # Variance is defined as 1/n * E[(x-mu)^2]. We consider our X to be a
    # stream of n instances of [0,1] values; 1 if item appears in a transaction,
    # 0 if not. We know that the average is count/n, and that X is 1
    # count times, and 0 (n-count) times, so the variance then becomes:
    # 1/n * (count * (1 - mean)^2 + (n-count) * (0 - mean)^2).
    mean = count / n
    return (count * (1 - mean)**2 + (n - count) * (0 - mean)**2) / n


def hoeffding_bound(a_mean, a_len, b_mean, b_len, confidence):
    # Returns true if we can't reject null hypothesis that the populations are
    # the same given confidence value.
    n = a_mean + b_mean
    v = variance(n, a_len + b_len)
    m = 1 / ((1 / a_len) + (1 / b_len))
    delta_prime = math.log(
        2 * math.log(a_len + b_len) / confidence)
    epsilon = (math.sqrt((2 / m) * v * delta_prime)
               + (2 / (3 * m) * delta_prime))
    assert(epsilon >= 0 and epsilon <= 1)
    return abs(a_mean - b_mean) < epsilon
