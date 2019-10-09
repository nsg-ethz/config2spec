#!/usr/bin/env python
# Author: Ruediger Birkner (Networked Systems Group at ETH Zurich)

import unittest

from ipaddress import IPv4Network
from ipaddress import IPv4Address

from config2spec.dataplane.fecs import FECFinder
from config2spec.dataplane.fecs import EquivalenceClass
from config2spec.dataplane.fecs import DisjointECException


class FECTest(unittest.TestCase):
    def setUp(self):
        self.test_pairs = [
            ("64.57.18.192/29", "01000000001110010001001011000", 29),
            ("64.57.25.0/27", "010000000011100100011001000", 27),
            ("156.56.6.0/24", "100111000011100000000110", 24),
            ("0.0.0.0/0", "", 0),
            ("1.1.1.1/32", "00000001000000010000000100000001", 32)
        ]

    def test_get_all_fecs_full(self):
        prefixes = [
            "1.1.1.1/32",
            "64.57.18.192/29",
            "64.57.25.0/27",
            "156.56.6.0/24",
            "0.0.0.0/0",
            "10.0.0.0/8",
            "10.12.0.0/16",
            "10.12.192.0/20",
            "10.12.253.0/24",
        ]

        starts_ends = [
            (0, 16843008),
            (16843009, 16843009),
            (16843010, 167772159),
            (167772160, 168558591),
            (168558592, 168607743),
            (168607744, 168611839),
            (168611840, 168623359),
            (168623360, 168623615),
            (168623616, 168624127),
            (168624128, 184549375),
            (184549376, 1077482175),
            (1077482176, 1077482183),
            (1077482184, 1077483775),
            (1077483776, 1077483807),
            (1077483808, 2620917247),
            (2620917248, 2620917503),
            (2620917504, 4294967295),
        ]

        fecs = list()
        for start, end in starts_ends:
            tmp = EquivalenceClass()
            tmp.first = start
            tmp.last = end
            fecs.append(tmp)

        fec = FECFinder()
        for str_prefix in prefixes:
            prefix = IPv4Network(str_prefix)
            fec.insert_prefix(prefix)

        all_fecs = fec.get_all_fecs()

        self.assertCountEqual(all_fecs, fecs)

    def test_get_all_fecs_sparse(self):
        prefixes = [
            "1.1.1.1/32",
            "64.57.18.192/29",
            "64.57.25.0/27",
            "156.56.6.0/24",
            "10.0.0.0/8",
        ]

        starts_ends = [
            (16843009, 16843009),
            (167772160, 184549375),
            (1077482176, 1077482183),
            (1077483776, 1077483807),
            (2620917248, 2620917503),
        ]

        fecs = list()
        for start, end in starts_ends:
            tmp = EquivalenceClass()
            tmp.first = start
            tmp.last = end
            fecs.append(tmp)

        fec = FECFinder()
        for str_prefix in prefixes:
            prefix = IPv4Network(str_prefix)
            fec.insert_prefix(prefix)

        all_fecs = fec.get_all_fecs()

        self.assertCountEqual(all_fecs, fecs)

    def test_get_all_prefixes(self):
        prefixes = [
            IPv4Network("1.1.1.1/32"),
            IPv4Network("64.57.18.192/29"),
            IPv4Network("64.57.25.0/27"),
            IPv4Network("156.56.6.0/24"),
            IPv4Network("0.0.0.0/0"),
            IPv4Network("10.0.0.0/8"),
            IPv4Network("10.12.0.0/16"),
            IPv4Network("10.12.192.0/20"),
            IPv4Network("10.12.253.0/24"),
        ]

        fec = FECFinder()
        for prefix in prefixes:
            fec.insert_prefix(prefix)

        all_prefixes = fec.get_all_prefixes()

        self.assertCountEqual(all_prefixes, prefixes)

    def test_bitstring_to_ipv4(self):
        fec = FECFinder()

        for str_prefix, bitstring, prefix_len in self.test_pairs:
            prefix = IPv4Network(str_prefix)
            self.assertEqual(prefix, fec.bitstring_to_ipv4(bitstring))

    def test_ipv4_to_bitstring(self):
        fec = FECFinder()

        for str_prefix, bitstring, prefix_len in self.test_pairs:
            prefix = IPv4Network(str_prefix)
            self.assertEqual(fec.ipv4_to_bitstring(prefix), (bitstring, prefix_len))


class EquivalenceClassTest(unittest.TestCase):

    def test_add_bitstring_joint(self):
        joint_prefixes = [
            (IPv4Network("10.1.0.0/16"), "0000101000000001"),
            (IPv4Network("10.1.12.0/24"), "000010100000000100001100"),
            (IPv4Network("10.1.128.0/19"), "0000101000000001100"),
            (IPv4Network("10.0.255.0/24"), "000010100000000011111111"),
            (IPv4Network("10.0.0.0/16"), "0000101000000000"),
            (IPv4Network("10.0.0.0/8"), "00001010")
        ]

        ec = EquivalenceClass()

        for prefix, bitstring in joint_prefixes:
            try:
                ec.add_bitstring(bitstring)
            except DisjointECException:
                self.fail("add_bitstring({prefix}) raised DisjointECException unexpectedly!".format(prefix=prefix))

    def test_add_bitstring_disjoint(self):
        ec = EquivalenceClass()
        ec.add_bitstring("0000101000000001")  # 10.1.0.0/16
        self.assertRaises(DisjointECException, ec.add_bitstring, "000101010000000000000000")  # 21.0.0.0/24

    def test_add_prefix_joint(self):
        joint_prefixes = [
            (IPv4Network("10.1.0.0/16"), "0000101000000001"),
            (IPv4Network("10.1.12.0/24"), "000010100000000100001100"),
            (IPv4Network("10.1.128.0/19"), "0000101000000001100"),
            (IPv4Network("10.0.255.0/24"), "000010100000000011111111"),
            (IPv4Network("10.0.0.0/16"), "0000101000000000"),
            (IPv4Network("10.0.0.0/8"), "00001010")
        ]

        ec = EquivalenceClass()

        for prefix, bitstring in joint_prefixes:
            try:
                ec.add_prefix(prefix)
            except DisjointECException:
                self.fail("add_prefix({prefix}) raised DisjointECException unexpectedly!".format(prefix=prefix))

    def test_add_prefix_disjoint(self):
        ec = EquivalenceClass()
        ec.add_prefix(IPv4Network("10.1.0.0/16"))
        self.assertRaises(DisjointECException, ec.add_prefix, IPv4Network("21.0.0.0/24"))

    def test_add_prefix_simple(self):
        test_cases = [
            ([IPv4Network("64.57.31.248/32"), IPv4Network("64.57.31.246/31")], 1077485558, 1077485560),
            ([IPv4Network("10.1.0.0/16"), ], 167837696, 167903231),
            ([IPv4Network("0.0.0.0/0"), IPv4Network("10.0.0.252/30"), IPv4Network("10.0.1.0/24"), ], 0, 4294967295),
            ([IPv4Network("10.0.0.252/30"), IPv4Network("10.0.1.0/24"), ], 167772412, 167772671),
            ([IPv4Network("0.0.1.0/24"), IPv4Network("0.0.2.0/23")], 256, 1023)
        ]

        for prefixes, first, last in test_cases:
            ec = EquivalenceClass()
            for prefix in prefixes:
                ec.add_prefix(prefix)

            self.assertEqual(first, ec.first)
            self.assertEqual(last, ec.last)

    def test_get_ip_prefix(self):
        test_cases = [
            ([IPv4Network("10.1.0.0/16"), ], 5, IPv4Address("10.1.0.5")),
            ([IPv4Network("10.0.0.252/30"), IPv4Network("10.0.1.0/24"),], 10, IPv4Address("10.0.1.6")),
        ]

        for prefixes, item, ip_address in test_cases:
            ec = EquivalenceClass()
            for prefix in prefixes:
                ec.add_prefix(prefix)
            self.assertEqual(ip_address, ec.get_ip(item))

    def test_get_prefix_simple(self):
        test_cases = [
            (1077485558, 1077485560, IPv4Network("64.57.31.246/31")),
        ]

        for first, last, full_prefix in test_cases:
            ec = EquivalenceClass()
            ec.first = first
            ec.last = last
            self.assertEqual(full_prefix, ec.get_prefix())

    def test_get_prefix_prefix(self):
        test_cases = [
            ([IPv4Network("64.57.31.248/32"), IPv4Network("64.57.31.246/31")], IPv4Network("64.57.31.246/31")),
            ([IPv4Network("10.1.0.0/16"), ], IPv4Network("10.1.0.0/16")),
            ([IPv4Network("0.0.0.0/0"), IPv4Network("10.0.0.252/30"), IPv4Network("10.0.1.0/24"), ], IPv4Network("0.0.0.0/0")),
            ([IPv4Network("10.0.0.252/30"), IPv4Network("10.0.1.0/24"), ], IPv4Network("10.0.0.252/30")),
            ([IPv4Network("0.0.1.0/24"), IPv4Network("0.0.2.0/23")], IPv4Network("0.0.1.0/24"))
        ]

        for prefixes, full_prefix in test_cases:
            ec = EquivalenceClass()
            for prefix in prefixes:
                ec.add_prefix(prefix)
            self.assertEqual(full_prefix, ec.get_prefix())

    def test_get_ip_bitstring(self):
        test_cases = [
            (["0000101000000001", ], 5, IPv4Address("10.1.0.5")),  # 10.1.0.0/16
            (["000010100000000000000000111111", "000010100000000000000001", ], 10, IPv4Address("10.0.1.6")),  # 10.0.0.252/30, 10.0.1.0/24
        ]

        for prefixes, item, ip_address in test_cases:
            ec = EquivalenceClass()
            for prefix in prefixes:
                ec.add_bitstring(prefix)
            self.assertEqual(ip_address, ec.get_ip(item))

    def test_get_all_prefixes(self):
        test_cases = [
            [IPv4Network("64.57.31.248/32"), IPv4Network("64.57.31.246/31")],
            [IPv4Network("10.1.0.0/16"), ],
            [IPv4Network("10.0.0.252/30"), IPv4Network("10.0.1.0/24"), ],
            [IPv4Network("0.0.1.0/24"), IPv4Network("0.0.2.0/23")],
        ]

        for prefixes in test_cases:
            ec = EquivalenceClass()
            for prefix in prefixes:
                ec.add_prefix(prefix)
            self.assertCountEqual(prefixes, ec.get_all_prefixes())

    def test_get_prefix_bitstring(self):
        test_cases = [
            (["0000101000000000", ], IPv4Network("10.0.0.0/16")),  # 10.0.0.0/16
            (["", "000010100000000000000000111111", "000010100000000000000000",], IPv4Network("0.0.0.0/0")),  # 0.0.0.0/0, 10.0.0.252/30, 10.0.1.0/24
            (["000010100000000000000000111111", "000010100000000000000001",], IPv4Network("10.0.0.252/30")),  # 10.0.0.252/30, 10.0.1.0/24
            (["000000000000000000000001", "00000000000000000000001"], IPv4Network("0.0.1.0/24"))  # 0.0.1.0/24, 0.0.2.0/23
        ]

        for prefixes, full_prefix in test_cases:
            ec = EquivalenceClass()
            for prefix in prefixes:
                ec.add_bitstring(prefix)
            self.assertEqual(full_prefix, ec.get_prefix())


if __name__ == "__main__":
    unittest.main()
