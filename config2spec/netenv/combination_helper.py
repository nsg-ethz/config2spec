#!/usr/bin/env python
# Author: Ruediger Birkner (Networked Systems Group at ETH Zurich)

# taken from https://stackoverflow.com/a/36345790/2373793


def num_items(n, max_k):
    count = 0
    for k in range(0, max_k + 1):
        count += choose(n, k)
    return count


def map_item_to_index(item, n, max_k):
    for k in range(0, max_k + 1):
        item_count = choose(n, k)
        if item >= item_count:
            item -= item_count
        else:
            return item, k

    return choose(n, max_k) - 1, max_k


def choose(n, k):
    '''Returns the number of ways to choose k items from n items'''
    reflect = n - k
    if k > reflect:
        if k > n:
            return 0
        k = reflect
    if k == 0:
        return 1
    for n_minus_i_plus_1, i in zip(range(n - 1, n - k, -1), range(2, k + 1)):
        n = n * n_minus_i_plus_1 // i
    return n


def nth_combination(index, n, k):
    '''
    Yields the items of the single combination that would be at the provided (0-based) index in a lexicographically
    sorted list of combinations of choices of k items from n items [0,n), given the combinations were sorted in
    descending order. Yields in descending order.
    '''

    n_choose_k = 1
    for n_minus_i, i_plus_1 in zip(range(n, n - k, -1), range(1, k + 1)):
        n_choose_k *= n_minus_i
        n_choose_k //= i_plus_1
    curr_index = n_choose_k

    combination = set()
    for k in range(k, 0, -1):
        n_choose_k *= k
        n_choose_k //= n
        while curr_index - n_choose_k > index:
            curr_index -= n_choose_k
            n_choose_k *= (n - k)
            n_choose_k -= n_choose_k % k
            n -= 1
            n_choose_k //= n
        n -= 1
        combination.add(n)

    return combination


def index_of_combination(combination):
    '''
    Returns the (0-based) index the given combination would have if it were in a reverse-lexicographically
    sorted list of combinations of choices of len(combination) items from any possible number of items (given the
    combination's length and maximum value) - combination must already be in descending order, and it's items
    drawn from the set [0,n).
    '''

    result = 0
    for i, a in enumerate(combination):
        result += choose(a, i + 1)
    return result
