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


from typing import List, Optional

import numpy as np
from sklearn.metrics import confusion_matrix


def print_confusion_matrix(
        y_true: np.ndarray,
        y_pred: np.ndarray,
        labels: Optional[List] = None,
        hide_zeroes: bool = False,
        hide_diagonal: bool = False,
        hide_threshold: Optional[float] = None,
):
    """Print a nicely formatted confusion matrix with labelled rows and columns.

    Predicted labels are in the top horizontal header, true labels on the
        vertical header.

    Args:
        y_true (np.ndarray): ground truth labels
        y_pred (np.ndarray): predicted labels
        labels (Optional[List], optional): list of all labels. If None, then
            all labels present in the data are displayed. Defaults to None.
        hide_zeroes (bool, optional): replace zero-values with an empty cell.
            Defaults to False.
        hide_diagonal (bool, optional): replace true positives (diagonal) with
            empty cells. Defaults to False.
        hide_threshold (Optional[float], optional): replace values below this
            threshold with empty cells. Set to None
            to display all values. Defaults to None.
    """
    if labels is None:
        labels = np.unique(np.concatenate((y_true, y_pred)))
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    # find which fixed column width will be used for the matrix
    columnwidth = max(
        [len(str(x)) for x in labels] + [5]
    )  # 5 is the minimum column width, otherwise the longest class name
    empty_cell = ' ' * columnwidth

    # top-left cell of the table that indicates that top headers are predicted
    # classes, left headers are true classes
    padding_fst_cell = (columnwidth - 3) // 2  # double-slash is int division
    fst_empty_cell = padding_fst_cell * ' ' + 't/p' + ' ' * (
                columnwidth - padding_fst_cell - 3)

    # Print header
    print('    ' + fst_empty_cell, end=' ')
    for label in labels:
        print(f'{label:{columnwidth}}',
              end=' ')  # right-aligned label padded with spaces to columnwidth

    print()  # newline
    # Print rows
    for i, label in enumerate(labels):
        print(f'    {label:{columnwidth}}',
              end=' ')  # right-aligned label padded with spaces to columnwidth
        for j in range(len(labels)):
            # cell value padded to columnwidth with spaces and displayed with
            # one decimal
            cell = f'{cm[i, j]:{columnwidth}.1f}'
            if hide_zeroes:
                cell = cell if float(cm[i, j]) != 0 else empty_cell
            if hide_diagonal:
                cell = cell if i != j else empty_cell
            if hide_threshold:
                cell = cell if cm[i, j] > hide_threshold else empty_cell
            print(cell, end=' ')
        print()
