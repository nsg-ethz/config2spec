#!/usr/bin/env python
# Author: Ruediger Birkner (Networked Systems Group at ETH Zurich)

import unittest

from config2spec.backend.query import Query
from config2spec.backend.response import Response
from config2spec.netenv.network_environment import NetworkEnvironment
from config2spec.policies.policy import PolicyDestination
from config2spec.policies.policy import PolicySource
from config2spec.policies.policy import PolicyType
from config2spec.topology.links import Link
from config2spec.topology.links import LinkState


class ResponseTest(unittest.TestCase):
    def test_parse_flow_counterexample(self):
        tests = [
            self.get_single_flow_counter_example(),
            self.get_multi_flow_counter_example(),
        ]

        i = 0
        for _, message, correct_failed_links, correct_src_routers in tests:
            i += 1

            test_failed_links, test_src_routers = Response.parse_flow_counterexample(message)

            self.assertEqual(test_failed_links, correct_failed_links, "Test {id}".format(id=i))
            self.assertEqual(test_src_routers, correct_src_routers, "Test {id}".format(id=i))

    def test_parse_generic_counterexample(self):
        tests = [
            self.get_generic_single_counter_example(),
        ]

        for _, message, correct_failed_links, correct_src_routers in tests:
            test_failed_links, test_src_routers = Response.parse_generic_counterexample(message)

            self.assertEqual(test_failed_links, correct_failed_links)
            self.assertEqual(test_src_routers, correct_src_routers)

    def test_full(self):
        tests = [
            self.get_single_flow_counter_example(),
            self.get_multi_flow_counter_example(),
        ]

        for query, response, correct_failed_links, correct_src_routers in tests:
            correct_failed_sources = list()
            correct_success_sources = list()
            for source in query.sources:
                if source.router in correct_src_routers:
                    correct_failed_sources.append(source)
                else:
                    correct_success_sources.append(source)
            all_hold = len(correct_failed_sources) == 0

            response = Response(query, response)
            self.assertEqual(response.all_hold(), all_hold)
            self.assertCountEqual(response.holds_not(), correct_failed_sources)
            self.assertCountEqual(response.holds(), correct_success_sources)

    @staticmethod
    def get_all_edges():
        return [
            ("r1", "r2"), ("r1", "r6"), ("r2", "r3"), ("r2", "r7"), ("r3", "r4"), ("r3", "r8"), ("r4", "r5"),
            ("r4", "r9"), ("r5", "r10"), ("r6", "r7"), ("r6", "r11"), ("r7", "r8"), ("r7", "r12"), ("r8", "r9"),
            ("r8", "r13"), ("r9", "r10"), ("r9", "r14"), ("r10", "r15"), ("r11", "r12"), ("r11", "r16"),
            ("r12", "r13"), ("r12", "r17"), ("r13", "r14"), ("r13", "r18"), ("r14", "r15"), ("r14", "r19"),
            ("r15", "r20"), ("r16", "r17"), ("r16", "r21"), ("r17", "r18"), ("r17", "r22"), ("r18",   "r19"),
            ("r18", "r23"), ("r19", "r20"), ("r19", "r24"), ("r20", "r25"), ("r21", "r22"), ("r22", "r23"),
            ("r23", "r24"), ("r24", "r25")
        ]

    @staticmethod
    def get_query(sources):
        sources = [PolicySource(src_router) for src_router in sources]
        destinations = PolicyDestination("r12", "FastEthernet1/1", "11.0.12.0/24")
        num_paths = 3
        links = [Link("l{id}".format(id=i), edge, LinkState.UP) for i, edge in enumerate(ResponseTest.get_all_edges())]
        netenv = NetworkEnvironment(links)

        return Query(PolicyType.LoadBalancingSimple, sources, destinations, num_paths, netenv, negate=False)

    @staticmethod
    def get_generic_single_counter_example():
        query = ResponseTest.get_query(sources=["r6"])

        response = ("Counterexample Found:\n"
                    "==========================================\n"
                    "Packet:\n"
                    "----------------------\n"
                    "dstIp: 11.12.7.2\n"
                    "\n"
                    "Environment Messages:\n"
                    "----------------------\n"
                    "Final Forwarding:\n"
                    "----------------------\n"
                    "r10,FastEthernet1/0 --> r9,FastEthernet0/0 (OSPF)\n"
                    "r11,FastEthernet0/0 --> r12,FastEthernet1/0 (OSPF)\n"
                    "r13,FastEthernet1/1 --> r8,FastEthernet0/1 (OSPF)\n"
                    "r14,FastEthernet1/0 --> r13,FastEthernet0/0 (OSPF)\n"
                    "r15,FastEthernet1/0 --> r14,FastEthernet0/0 (OSPF)\n"
                    "r15,FastEthernet1/1 --> r10,FastEthernet0/1 (OSPF)\n"
                    "r17,FastEthernet1/1 --> r12,FastEthernet0/1 (OSPF)\n"
                    "r18,FastEthernet1/0 --> r17,FastEthernet0/0 (OSPF)\n"
                    "r19,FastEthernet1/0 --> r18,FastEthernet0/0 (OSPF)\n"
                    "r2,FastEthernet0/1 --> r7,FastEthernet1/1 (OSPF)\n"
                    "r20,FastEthernet1/1 --> r15,FastEthernet0/1 (OSPF)\n"
                    "r24,FastEthernet1/1 --> r19,FastEthernet0/1 (OSPF)\n"
                    "r25,FastEthernet1/1 --> r20,FastEthernet0/1 (OSPF)\n"
                    "r3,FastEthernet0/1 --> r8,FastEthernet1/1 (OSPF)\n"
                    "r4,FastEthernet0/0 --> r5,FastEthernet1/0 (OSPF)\n"
                    "r5,FastEthernet0/1 --> r10,FastEthernet1/1 (OSPF)\n"
                    "r6,FastEthernet0/1 --> r11,FastEthernet1/1 (OSPF)\n"
                    "r7,FastEthernet0/1 --> r12,FastEthernet1/1 (CONNECTED)\n"
                    "r8,FastEthernet1/0 --> r7,FastEthernet0/0 (OSPF)\n"
                    "r9,FastEthernet1/0 --> r8,FastEthernet0/0 (OSPF)\n"
                    "\n"
                    "Failures:\n"
                    "----------------------\n"
                    "link(r1,r2)\n"
                    "link(r1,r6)\n"
                    "link(r11,r16)\n"
                    "link(r12,r13)\n"
                    "link(r14,r9)\n"
                    "link(r16,r17)\n"
                    "link(r16,r21)\n"
                    "link(r17,r22)\n"
                    "link(r18,r23)\n"
                    "link(r19,r20)\n"
                    "link(r2,r3)\n"
                    "link(r21,r22)\n"
                    "link(r22,r23)\n"
                    "link(r23,r24)\n"
                    "link(r24,r25)\n"
                    "link(r3,r4)\n"
                    "link(r4,r9)\n"
                    "link(r6,r7)\n"
                    "==========================================")

        failed_edges = [("r1", "r2"), ("r1", "r6"), ("r11", "r16"), ("r12", "r13"), ("r14", "r9"), ("r16", "r17"),
                        ("r16", "r21"), ("r17", "r22"), ("r18", "r23"), ("r19", "r20"), ("r2", "r3"), ("r21", "r22"),
                        ("r22", "r23"), ("r23", "r24"), ("r24", "r25"), ("r3", "r4"), ("r4", "r9"), ("r6", "r7")]
        failed_links = set([Link.get_name(r1, r2) for r1, r2 in failed_edges])

        src_routers = set()

        return query, response, failed_links, src_routers

    @staticmethod
    def get_single_flow_counter_example():
        query = ResponseTest.get_query(sources=["r12"])

        response = ("Flow: ingress:r12 vrf:default 0.0.0.0->11.15.10.2 HOPOPT packetLength:0 state:NEW\n"
                    "  environment:BASE\n"
                    "Environment{testrigName=tempSnapshot, edgeBlacklist=[], interfaceBlacklist=null, "
                    "nodeBlacklist=null, bgpTables=null, routingTables=null, externalBgpAnnouncements=[]}\n"
                    "    Hop 1: r12:FastEthernet0/0 -> r13:FastEthernet1/0\n"
                    "    Hop 2: r13:FastEthernet0/0 -> r14:FastEthernet1/0\n"
                    "    Hop 3: r14:FastEthernet0/0 -> r15:FastEthernet1/0\n"
                    "    ACCEPTED\n"
                    "\n")

        failed_links = set()

        src_routers = {"r12"}

        return query, response, failed_links, src_routers

    @staticmethod
    def get_multi_flow_counter_example():
        query = ResponseTest.get_query(sources=["r15", "r6"])

        response = ("Flow: ingress:r15 vrf:default 0.0.0.0->11.12.7.2 HOPOPT packetLength:0 state:NEW\n"
                    "  environment:BASE\n"
                    "Environment{testrigName=tempSnapshot, edgeBlacklist=[<r11:FastEthernet0/1, r16:FastEthernet1/1>, "
                    "<r12:FastEthernet0/0, r13:FastEthernet1/0>, <r16:FastEthernet0/0, r17:FastEthernet1/0>, "
                    "<r16:FastEthernet0/1, r21:FastEthernet1/1>, <r17:FastEthernet0/1, r22:FastEthernet1/1>, "
                    "<r18:FastEthernet0/1, r23:FastEthernet1/1>, <r19:FastEthernet0/0, r20:FastEthernet1/0>, "
                    "<r2:FastEthernet0/0, r3:FastEthernet1/0>, <r2:FastEthernet1/0, r1:FastEthernet0/0>, "
                    "<r21:FastEthernet0/0, r22:FastEthernet1/0>, <r23:FastEthernet0/0, r24:FastEthernet1/0>, "
                    "<r23:FastEthernet1/0, r22:FastEthernet0/0>, <r25:FastEthernet1/0, r24:FastEthernet0/0>, "
                    "<r3:FastEthernet0/0, r4:FastEthernet1/0>, <r4:FastEthernet0/1, r9:FastEthernet1/1>, "
                    "<r6:FastEthernet0/0, r7:FastEthernet1/0>, <r6:FastEthernet1/1, r1:FastEthernet0/1>, "
                    "<r9:FastEthernet0/1, r14:FastEthernet1/1>], interfaceBlacklist=null, nodeBlacklist=null, "
                    "bgpTables=null, routingTables=null, externalBgpAnnouncements=[]}\n"
                    "    Hop 1: r15:FastEthernet1/1 -> r10:FastEthernet0/1\n"
                    "    Hop 2: r10:FastEthernet1/0 -> r9:FastEthernet0/0\n"
                    "    Hop 3: r9:FastEthernet1/0 -> r8:FastEthernet0/0\n"
                    "    Hop 4: r8:FastEthernet1/0 -> r7:FastEthernet0/0\n"
                    "    Hop 5: r7:FastEthernet0/1 -> r12:FastEthernet1/1\n"
                    "    ACCEPTED\n\n"
                    "Flow: ingress:r6 vrf:default 0.0.0.0->11.12.7.2 HOPOPT packetLength:0 state:NEW\n"
                    "  environment:BASE\n"
                    "Environment{testrigName=tempSnapshotId, edgeBlacklist=["
                    "<r11:FastEthernet0/1, r16:FastEthernet1/1>, <r12:FastEthernet0/0, r13:FastEthernet1/0>, "
                    "<r16:FastEthernet0/0, r17:FastEthernet1/0>, <r16:FastEthernet0/1, r21:FastEthernet1/1>, "
                    "<r17:FastEthernet0/1, r22:FastEthernet1/1>, <r18:FastEthernet0/1, r23:FastEthernet1/1>, "
                    "<r19:FastEthernet0/0, r20:FastEthernet1/0>, <r2:FastEthernet0/0, r3:FastEthernet1/0>, "
                    "<r2:FastEthernet1/0, r1:FastEthernet0/0>, <r21:FastEthernet0/0, r22:FastEthernet1/0>, "
                    "<r23:FastEthernet0/0, r24:FastEthernet1/0>, <r23:FastEthernet1/0, r22:FastEthernet0/0>, "
                    "<r25:FastEthernet1/0, r24:FastEthernet0/0>, <r3:FastEthernet0/0, r4:FastEthernet1/0>, "
                    "<r4:FastEthernet0/1, r9:FastEthernet1/1>, <r6:FastEthernet0/0, r7:FastEthernet1/0>, "
                    "<r6:FastEthernet1/1, r1:FastEthernet0/1>, <r9:FastEthernet0/1, r14:FastEthernet1/1>], "
                    "interfaceBlacklist=null, nodeBlacklist=null, "
                    "bgpTables=null, routingTables=null, externalBgpAnnouncements=[]}\n"
                    "    Hop 1: r6:FastEthernet0/1 -> r11:FastEthernet1/1\n"
                    "    Hop 2: r11:FastEthernet0/0 -> r12:FastEthernet1/0\n"
                    "    ACCEPTED")

        failed_edges = [("r12", "r13"), ("r16", "r17"), ("r16", "r21"), ("r17", "r22"), ("r18", "r23"),
                        ("r19", "r20"), ("r2", "r3"), ("r2", "r1"), ("r21", "r22"), ("r23", "r24"),
                        ("r23", "r22"), ("r25", "r24"), ("r3", "r4"), ("r4", "r9"), ("r6", "r7"),
                        ("r6", "r1"), ("r9", "r14"), ("r16", "r11"), ]
        failed_links = set([Link.get_name(r1, r2) for r1, r2 in failed_edges])

        src_routers = {"r15", "r6"}

        return query, response, failed_links, src_routers

    @staticmethod
    def get_multi_flow_counter_example2():
        query = ResponseTest.get_query(sources=["r15", "r6"])

        response = "Verified"

        failed_links = set(),

        src_routers = {"r15", "r6"}

        return query, response, failed_links, src_routers


if __name__ == "__main__":
    unittest.main()
