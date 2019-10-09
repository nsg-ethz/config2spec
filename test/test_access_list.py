#!/usr/bin/env python
# Author: Ruediger Birkner (Networked Systems Group at ETH Zurich)


import unittest

from ipaddress import IPv4Network

from config2spec.topology.access_list import AccessList
from config2spec.topology.access_list import ACLEntry
from config2spec.topology.access_list import ACLType


class AccessListTest(unittest.TestCase):
    def test_pass_through_string(self):
        access_list = AccessList("test")

        access_list.add_permit("99.99.99.0/24", "12.13.14.0/24")
        access_list.add_deny("99.99.0.0/16", "0.0.0.0/0")
        access_list.add_permit("12.11.10.0/24", "8.0.0.0/8")
        access_list.add_deny("0.0.0.0/0", "8.8.8.0/24")

        tests = [
            (IPv4Network("99.99.99.128/28"), IPv4Network("12.13.14.32/30"), True),
            (IPv4Network("99.99.157.0/24"), IPv4Network("8.0.0.0/8"), False),
            (IPv4Network("12.11.10.0/31"), IPv4Network("8.8.8.0/24"), True),
            (IPv4Network("12.11.10.0/24"), IPv4Network("8.0.0.0/8"), True),
            (IPv4Network("33.22.11.0/31"), IPv4Network("8.8.8.0/24"), False),
            (IPv4Network("33.22.11.0/31"), IPv4Network("8.13.14.0/24"), False),
        ]

        i = 0
        for src_net, dst_net, result in tests:
            i += 1

            self.assertEqual(access_list.pass_through(src_net, dst_net), result, "Test {id}".format(id=i))

    def test_pass_through(self):
        access_list = AccessList("test")

        access_list.add_acl_entry(ACLType.PERMIT, IPv4Network("99.99.99.0/24"), IPv4Network("12.13.14.0/24"))
        access_list.add_acl_entry(ACLType.DENY, IPv4Network("99.99.0.0/16"), IPv4Network("0.0.0.0/0"))
        access_list.add_acl_entry(ACLType.PERMIT, IPv4Network("12.11.10.0/24"), IPv4Network("8.0.0.0/8"))
        access_list.add_acl_entry(ACLType.DENY, IPv4Network("0.0.0.0/0"), IPv4Network("8.8.8.0/24"))

        tests = [
            (IPv4Network("99.99.99.128/28"), IPv4Network("12.13.14.32/30"), True),
            (IPv4Network("99.99.157.0/24"), IPv4Network("8.0.0.0/8"), False),
            (IPv4Network("12.11.10.0/31"), IPv4Network("8.8.8.0/24"), True),
            (IPv4Network("12.11.10.0/24"), IPv4Network("8.0.0.0/8"), True),
            (IPv4Network("33.22.11.0/31"), IPv4Network("8.8.8.0/24"), False),
            (IPv4Network("33.22.11.0/31"), IPv4Network("8.13.14.0/24"), False),
        ]

        i = 0
        for src_net, dst_net, result in tests:
            i += 1

            self.assertEqual(access_list.pass_through(src_net, dst_net), result, "Test {id}".format(id=i))


class ACLEntryTest(unittest.TestCase):
    def test_apply_simple_match(self):
        tests = [
            (ACLType.PERMIT, IPv4Network("0.0.0.0/0"), IPv4Network("0.0.0.0/0"),
             IPv4Network("10.0.1.0/24"), IPv4Network("99.99.0.0/16")),
            (ACLType.DENY, IPv4Network("0.0.0.0/0"), IPv4Network("0.0.0.0/0"),
             IPv4Network("21.9.12.0/29"), IPv4Network("8.8.128.0/19")),
        ]

        for acl_type, acl_src_net, acl_src_net, test_src_net, test_dst_net in tests:
            acl = ACLEntry(acl_type, acl_src_net, acl_src_net)

            self.assertEqual(acl.apply(test_src_net, test_dst_net), acl_type)

    def test_apply_match(self):
        tests = [
            (ACLType.PERMIT, IPv4Network("10.0.0.0/23"), IPv4Network("99.0.0.0/8"),
             IPv4Network("10.0.1.0/24"), IPv4Network("99.99.0.0/16")),
            (ACLType.DENY, IPv4Network("20.0.0.0/7"), IPv4Network("8.8.128.0/18"),
             IPv4Network("21.9.12.0/29"), IPv4Network("8.8.128.0/19")),
            (ACLType.PERMIT, IPv4Network("0.0.0.0/0"), IPv4Network("8.0.0.0/8"),
             IPv4Network("21.9.12.0/29"), IPv4Network("8.8.128.0/19")),
            (ACLType.DENY, IPv4Network("21.9.12.0/29"), IPv4Network("0.0.0.0/0"),
             IPv4Network("21.9.12.0/29"), IPv4Network("8.8.128.0/19")),
        ]

        i = 0
        for acl_type, acl_src_net, acl_dst_net, test_src_net, test_dst_net in tests:
            i += 1

            acl = ACLEntry(acl_type, acl_src_net, acl_dst_net)
            self.assertEqual(acl.apply(test_src_net, test_dst_net), acl_type, "Test {id}".format(id=i))

    def test_apply_mismatch(self):
        tests = [
            (ACLType.PERMIT, IPv4Network("10.0.0.0/32"), IPv4Network("25.0.0.0/8"),
             IPv4Network("10.0.1.0/24"), IPv4Network("99.99.0.0/16")),
            (ACLType.DENY, IPv4Network("8.8.128.0/18"), IPv4Network("20.0.0.0/7"),
             IPv4Network("21.9.12.0/29"), IPv4Network("8.8.128.0/19")),
            (ACLType.PERMIT, IPv4Network("8.0.0.0/8"), IPv4Network("0.0.0.0/0"),
             IPv4Network("21.9.12.0/29"), IPv4Network("8.8.128.0/19")),
            (ACLType.DENY, IPv4Network("21.9.12.0/29"), IPv4Network("25.0.0.0/8"),
             IPv4Network("21.9.12.0/29"), IPv4Network("8.8.128.0/19")),
            (ACLType.PERMIT, IPv4Network("11.12.0.0/23"), IPv4Network("99.0.0.0/8"),
             IPv4Network("10.0.1.0/24"), IPv4Network("99.99.0.0/16")),
        ]

        i = 0
        for acl_type, acl_src_net, acl_dst_net, test_src_net, test_dst_net in tests:
            i += 1

            acl = ACLEntry(acl_type, acl_src_net, acl_dst_net)
            self.assertEqual(acl.apply(test_src_net, test_dst_net), None, "Test {id}".format(id=i))


if __name__ == "__main__":
    unittest.main()
