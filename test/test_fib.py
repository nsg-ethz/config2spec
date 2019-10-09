#!/usr/bin/env python
# Author: Ruediger Birkner (Networked Systems Group at ETH Zurich)

import unittest

from ipaddress import IPv4Network

from config2spec.dataplane.fib import ForwardingTable


class ForwardingTableTest(unittest.TestCase):
    def test_get_next_hop(self):
        ft = ForwardingTable()

        entries = [
            (IPv4Network("10.0.0.0/8"), "FastEthernet0/0", "OSPFRoute", "r1"),
            (IPv4Network("10.0.0.0/16"), "FastEthernet0/0", "OSPFRoute", "r2"),
            (IPv4Network("12.0.0.0/24"), "FastEthernet0/0", "OSPFRoute", "r3"),
            (IPv4Network("13.0.0.0/8"), "FastEthernet0/0", "OSPFRoute", "r4"),
            (IPv4Network("13.0.0.0/8"), "FastEthernet0/0", "OSPFRoute", "r5"),
        ]

        for prefix, interface, route_type, next_hop in entries:
            ft.add_entry(prefix, interface, route_type, next_hop)

        tests = [
            (IPv4Network("10.0.0.0/8"), ["r1"]),
            (IPv4Network("10.0.0.0/24"), ["r2"]),
            (IPv4Network("10.251.0.0/24"), ["r1"]),
            (IPv4Network("12.0.0.10/31"), ["r3"]),
            (IPv4Network("13.29.120.0/27"), ["r4", "r5"]),
            (IPv4Network("9.1.1.0/24"), []),
        ]

        for prefix, correct_next_hops in tests:
            next_hops = ft.get_next_hop(prefix)
            self.assertCountEqual(next_hops, correct_next_hops, "Mismatch for prefix {prefix}".format(prefix=prefix))


if __name__ == "__main__":
    unittest.main()
