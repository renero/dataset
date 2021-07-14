from functools import reduce
from itertools import combinations


def factorize(number):
    n = number
    ni = 0
    result = []
    divisor = 2
    while n != 1 and ni < number:
        if n % divisor == 0:
            n = n / divisor
            result.append(divisor)
        else:
            divisor += 1
        ni += 1
    return result


def get_all_pairs(factors):
    """
    Get all possible combinations of pairs of elements from the array,
    so that all elements are present in any of the elements of the pair
    """
    R = []
    S = set(range(len(factors)))
    for i in range(1, len(factors)):
        for comb in combinations(range(len(factors)), i):
            s1 = [factors[idx] for idx in comb]  # set(list(comb))
            c2 = S.difference(set(comb))
            s2 = [factors[idx] for idx in c2]
            R.append(tuple((tuple(s1), tuple(s2))))
    return R


def get_unique_pairs(pairs):
    S = set()
    sorted_pairs = [sorted(p) for p in pairs]
    for sp in sorted(sorted_pairs):
        S.add(tuple(sp))
    return S


def get_best_pair(unique_pairs):
    best_diff = 1000000
    best = None
    values = []
    for idx, pair in enumerate(unique_pairs):
        value = [reduce(lambda x, y: x * y, pair[i]) for i in range(len(pair))]
        diff = abs(value[0] - value[1])
        if diff < best_diff:
            best_diff = diff
            best = idx
        values.append(value)

    return values[best]


def get_best_factor(number):
    factors = factorize(number)
    if len(factors) == 1:
        return factors
    all_pairs = get_all_pairs(factors)
    unique_pairs = get_unique_pairs(all_pairs)
    best = get_best_pair(unique_pairs)
    return best


def find_best_factor(number):
    """
    Given a number, this method returns the closest and most similar
    pair of values that when multipled produce a value which is the exact
    number or one very close to it.
    This method is originally conceived to provide a good distribution of
    `number` plots in a 2D distribution.

    Example:
        >>> find_best_factor(14)
        [5, 3]
        >>> find_best_factor(23)
        [6, 4]

    Args:
        number: int, a number. Usuarlly 0 << number << 100

    Returns:
        An array with two elements on it (int).
    """
    i = number
    found = False
    p = []
    while not found:
        p = get_best_factor(i)
        if len(p) > 1:
            diff = abs(p[0] - p[1])
            if diff < min(p):
                found = True
        i += 1
    return sorted(p, reverse=True)
