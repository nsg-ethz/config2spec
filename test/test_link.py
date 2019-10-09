#!/usr/bin/env python
# Author: Ruediger Birkner (Networked Systems Group at ETH Zurich)

import random
import unittest

from ipaddress import IPv4Network

from config2spec.topology.links import Link
from config2spec.topology.links import LinkState


class LinkTest(unittest.TestCase):
    def get_random_link(self):
        link_id = "l{id}".format(id=random.randint(1, 100))
        edge = ("r{id}".format(id=random.randint(1, 100)), "r{id}".format(id=random.randint(1, 100)))
        state = random.choice([LinkState.UP, LinkState.DOWN, LinkState.SYMBOLIC])
        return link_id, edge, state

    def test_equality_equal(self):
        for _ in range(0, 100):
            link_id, edge, state = self.get_random_link()

            l1 = Link(link_id, edge, state)
            l2 = Link(link_id, edge, state)

            self.assertEqual(l1, l2)

    def test_equality_not_equal(self):
        for _ in range(0, 100):
            link_id1, edge1, state1 = self.get_random_link()
            link_id2, edge2, state2 = self.get_random_link()

            if link_id1 != link_id2 or edge1 != edge2 or state1 != state2:
                l1 = Link(link_id1, edge1, state1)
                l2 = Link(link_id2, edge2, state2)

                self.assertNotEqual(l1, l2)

    def test_get_polish_notation(self):
        for _ in range(0, 100):
            link_id, edge, state = self.get_random_link()
            link = Link(link_id, edge, state)

            if state == LinkState.SYMBOLIC:
                self.assertRaises(AssertionError, link.get_polish_notation)
            else:
                correct_pn = "= ( {variable} ) ( {state} )".format(variable=link.name,
                                                                   state=1 if state == LinkState.DOWN else 0)
                test_pn = link.get_polish_notation()
                self.assertEqual(test_pn, correct_pn)


if __name__ == "__main__":
    unittest.main()
