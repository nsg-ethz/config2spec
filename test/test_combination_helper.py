#!/usr/bin/env python
# Author: Ruediger Birkner (Networked Systems Group at ETH Zurich)

import unittest
import math
import random

from config2spec.netenv.combination_helper import choose
from config2spec.netenv.combination_helper import map_item_to_index
from config2spec.netenv.combination_helper import num_items
from config2spec.netenv.combination_helper import nth_combination
from config2spec.netenv.combination_helper import index_of_combination


class ForwardingTableTest(unittest.TestCase):
    def test_choose(self):
        def n_c_k(n, k):
            return int(math.factorial(n)//(math.factorial(k) * math.factorial(n - k)))

        for i in range(100):
            n = random.randint(1, 1000)
            k = random.randint(0, n)

            self.assertEqual(choose(n, k), n_c_k(n, k))

    def test_map_item_to_index(self):
        tests = [
            (0, 100, 3, 0, 0),
            (1, 100, 3, 0, 1),
            (59, 100, 3, 58, 1),
            (99, 100, 3, 98, 1),
            (100, 100, 3, 99, 1),
            (101, 100, 3, 0, 2),
            (115, 100, 3, 14, 2),
            (4500, 100, 3, 4399, 2),
            (10000, 100, 3, 4949, 3),
            (166750, 100, 3, 161699, 3),
            (166751, 100, 3, 161699, 3),
            (300000, 100, 3, 161699, 3),
        ]

        for item, n, max_k, index, k in tests:
            self.assertEqual(map_item_to_index(item, n, max_k), (index, k))

    def test_num_items(self):
        def n_c_k(n, k):
            return int(math.factorial(n)//(math.factorial(k) * math.factorial(n - k)))

        for i in range(100):
            n = random.randint(1, 1000)
            max_k = random.randint(0, n)

            count = sum(n_c_k(n, k) for k in range(0, max_k + 1))
            self.assertEqual(num_items(n, max_k), count)

    def test_nth_combination(self):
        tests = [
            (0, 10, 3, {0, 1, 2}),
            (5, 10, 3, {0, 2, 4}),
            (19, 10, 3, {3, 4, 5}),
        ]

        for index, n, max_k, combination in tests:
            self.assertEqual(nth_combination(index, n, max_k), combination)

    def test_index_of_combination(self):
        tests = [
            (0, 10, 3, {0, 1, 2}),
            (5, 10, 3, {0, 2, 4}),
            (19, 10, 3, {3, 4, 5}),
        ]

        for index, n, max_k, combination in tests:
            self.assertEqual(index_of_combination(combination), index)


if __name__ == "__main__":
    unittest.main()
