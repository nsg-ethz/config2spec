#!/usr/bin/env python
# Author: Ruediger Birkner (Networked Systems Group at ETH Zurich)

import networkx as nx

import unittest

from ipaddress import IPv4Network

from config2spec.policies.policy_guesser import PolicyGuesser
from config2spec.policies.policy import PolicyType
from config2spec.policies.policy import PolicyDestination
from config2spec.policies.policy import PolicySource
from config2spec.topology.interface import Interface


class DummyNetwork(object):
    def __init__(self, nodes, interfaces):
        self.interfaces = interfaces
        self.all_nodes = nodes

    def get_interfaces_for_subnet(self, router, subnet):
        # TODO adapt to reality with overlapping prefixes
        return self.interfaces[subnet]

    def nodes(self):
        return self.all_nodes


class PolicyGuessTest(unittest.TestCase):
    def get_simple_network(self, local=False):
        subnet = IPv4Network("10.0.0.0/24")

        # normal forwarding graph
        fwd_graph = nx.DiGraph()
        fwd_graph.add_edge("r1", "sink")
        fwd_graph.add_edge("r2", "r1")
        fwd_graph.add_edge("r3", "r1")
        fwd_graph.add_edge("r4", "r2")
        fwd_graph.add_edge("r5", "r2")
        fwd_graph.add_edge("r5", "r4")
        fwd_graph.add_edge("r6", "r3")

        # according to the definition in https://en.wikipedia.org/wiki/Dominator_(graph_theory)
        dom_graph = nx.DiGraph()
        dom_graph.add_edge("r1", "sink")
        dom_graph.add_edge("r2", "r1")
        dom_graph.add_edge("r3", "r1")
        dom_graph.add_edge("r4", "r2")
        dom_graph.add_edge("r5", "r2")
        dom_graph.add_edge("r6", "r3")

        fwd_graphs = {subnet: fwd_graph}
        dom_graphs = {subnet: dom_graph}

        # dummy network
        nodes = ["r1", "r2", "r3", "r4", "r5", "r6", ]
        dst_router = "r1"
        dst_interface = Interface("FastEthernet0/0")
        dst_interface.set_ip_address(next(subnet.hosts()), subnet)
        interfaces = {subnet: [(dst_router, dst_interface), ]}
        network = DummyNetwork(nodes, interfaces)

        policy_destination = PolicyDestination(dst_router, dst_interface, subnet)

        reachability_policies = [
            (PolicyType.Reachability, policy_destination, 0, PolicySource("r2")),
            (PolicyType.Reachability, policy_destination, 0, PolicySource("r3")),
            (PolicyType.Reachability, policy_destination, 0, PolicySource("r4")),
            (PolicyType.Reachability, policy_destination, 0, PolicySource("r5")),
            (PolicyType.Reachability, policy_destination, 0, PolicySource("r6")),
        ]

        if local:
            reachability_policies.append((PolicyType.Reachability, policy_destination, 0, PolicySource("r1")))

        return network, fwd_graphs, dom_graphs, policy_destination, reachability_policies

    def get_disconnected_network(self, local=False):
        subnet = IPv4Network("10.0.0.0/24")

        # normal forwarding graph
        fwd_graph = nx.DiGraph()
        fwd_graph.add_edge("r1", "sink")
        fwd_graph.add_edge("r2", "r1")
        fwd_graph.add_edge("r3", "r2")
        fwd_graph.add_edge("r4", "r1")
        fwd_graph.add_edge("r4", "r2")
        fwd_graph.add_edge("r6", "r5")
        fwd_graph.add_edge("r7", "r6")
        fwd_graph.add_edge("r8", "r5")
        fwd_graph.add_edge("r8", "r6")

        # according to the definition in https://en.wikipedia.org/wiki/Dominator_(graph_theory)
        dom_graph = nx.DiGraph()
        dom_graph.add_edge("r1", "sink")
        dom_graph.add_edge("r2", "r1")
        dom_graph.add_edge("r3", "r2")
        dom_graph.add_edge("r4", "r1")

        fwd_graphs = {subnet: fwd_graph}
        dom_graphs = {subnet: dom_graph}

        # dummy network
        nodes = ["r1", "r2", "r3", "r4", "r5", "r6", "r7", "r8", ]
        dst_router = "r1"
        dst_interface = Interface("FastEthernet0/0")
        dst_interface.set_ip_address(next(subnet.hosts()), subnet)
        interfaces = {subnet: [(dst_router, dst_interface), ]}
        network = DummyNetwork(nodes, interfaces)

        policy_destination = PolicyDestination(dst_router, dst_interface, subnet)

        reachability_policies = [
            (PolicyType.Reachability, policy_destination, 0, PolicySource("r2")),
            (PolicyType.Reachability, policy_destination, 0, PolicySource("r3")),
            (PolicyType.Reachability, policy_destination, 0, PolicySource("r4")),
            (PolicyType.Isolation, policy_destination, 0, PolicySource("r5")),
            (PolicyType.Isolation, policy_destination, 0, PolicySource("r6")),
            (PolicyType.Isolation, policy_destination, 0, PolicySource("r7")),
            (PolicyType.Isolation, policy_destination, 0, PolicySource("r8")),
        ]

        if local:
            reachability_policies.append((PolicyType.Reachability, policy_destination, 0, PolicySource("r1")))

        return network, fwd_graphs, dom_graphs, policy_destination, reachability_policies

    def get_two_interfaces_network(self, local=False):
        subnet = IPv4Network("10.0.0.0/24")

        # normal forwarding graph
        fwd_graph = nx.DiGraph()
        fwd_graph.add_edge("r1", "sink")
        fwd_graph.add_edge("r2", "sink")
        fwd_graph.add_edge("r3", "r1")
        fwd_graph.add_edge("r4", "r1")
        fwd_graph.add_edge("r4", "r2")
        fwd_graph.add_edge("r5", "r2")
        fwd_graph.add_edge("r6", "r2")
        fwd_graph.add_edge("r6", "r5")

        # according to the definition in https://en.wikipedia.org/wiki/Dominator_(graph_theory)
        dom_graph = nx.DiGraph()
        dom_graph.add_edge("r1", "sink")
        dom_graph.add_edge("r2", "sink")
        dom_graph.add_edge("r3", "r1")
        dom_graph.add_edge("r4", "sink")
        dom_graph.add_edge("r5", "r2")
        dom_graph.add_edge("r6", "r2")

        fwd_graphs = {subnet: fwd_graph}
        dom_graphs = {subnet: dom_graph}

        # dummy network
        nodes = ["r1", "r2", "r3", "r4", "r5", "r6", ]
        dst_router1 = "r1"
        dst_router2 = "r2"
        dst_interface = Interface("FastEthernet0/0")
        dst_interface.set_ip_address(next(subnet.hosts()), subnet)
        interfaces = {subnet: [(dst_router1, dst_interface), (dst_router2, dst_interface), ]}
        network = DummyNetwork(nodes, interfaces)

        policy_destination1 = PolicyDestination(dst_router1, dst_interface, subnet)
        policy_destination2 = PolicyDestination(dst_router2, dst_interface, subnet)

        reachability_policies = [
            (PolicyType.Reachability, policy_destination1, 0, PolicySource("r3")),
            (PolicyType.Reachability, policy_destination1, 0, PolicySource("r4")),
            (PolicyType.Reachability, policy_destination2, 0, PolicySource("r4")),
            (PolicyType.Reachability, policy_destination2, 0, PolicySource("r5")),
            (PolicyType.Reachability, policy_destination2, 0, PolicySource("r6")),
        ]

        if local:
            reachability_policies.append((PolicyType.Reachability, policy_destination1, 0, PolicySource("r1")))
            reachability_policies.append((PolicyType.Reachability, policy_destination2, 0, PolicySource("r2")))

        return network, fwd_graphs, dom_graphs, reachability_policies

    def test_get_reachability_policies_simple(self):
        network, fwd_graphs, dom_graphs, _, reachability_policies = self.get_simple_network()

        test_policies = list()
        pg = PolicyGuesser(network)
        pg.get_reachability_policies(test_policies, fwd_graphs, dom_graphs, node_local_reachability=False)

        self.assertCountEqual(test_policies, reachability_policies)

    def test_get_reachability_policies_disconnected(self):
        network, fwd_graphs, dom_graphs, _, reachability_policies = self.get_disconnected_network()

        test_policies = list()
        pg = PolicyGuesser(network)
        pg.get_reachability_policies(test_policies, fwd_graphs, dom_graphs, node_local_reachability=False)

        self.assertCountEqual(test_policies, reachability_policies)

    # def test_get_reachability_policies_two_interfaces(self):
    #     network, fwd_graphs, dom_graphs, reachability_policies = self.get_two_interfaces_network()
    #
    #     test_policies = list()
    #     pg = PolicyGuesser(network)
    #     pg.get_reachability_policies(test_policies, fwd_graphs, dom_graphs, node_local_reachability=False)
    #
    #     self.assertCountEqual(test_policies, reachability_policies)
    #
    # def test_get_reachability_policies_local_reachability(self):
    #     network, fwd_graphs, dom_graphs, reachability_policies = self.get_two_interfaces_network(local=True)
    #
    #     test_policies = list()
    #     pg = PolicyGuesser(network)
    #     pg.get_reachability_policies(test_policies, fwd_graphs, dom_graphs, node_local_reachability=True)
    #
    #     self.assertCountEqual(test_policies, reachability_policies)

    def test_get_loadbalancing_policies_simple(self):
        network, fwd_graphs, dom_graphs, policy_destination, _ = self.get_simple_network()

        correct_policies = [
            (PolicyType.LoadBalancingSimple, policy_destination, 2, PolicySource("r5")),
        ]

        test_policies = list()
        pg = PolicyGuesser(network)
        pg.get_loadbalancing_policies(test_policies, fwd_graphs, dom_graphs, simple=True, node_local_reachability=False)

        self.assertCountEqual(test_policies, correct_policies)

    def test_get_loadbalancing_policies_disconnected(self):
        network, fwd_graphs, dom_graphs, policy_destination, _ = self.get_disconnected_network()

        correct_policies = [
            (PolicyType.LoadBalancingSimple, policy_destination, 2, PolicySource("r4")),
        ]

        test_policies = list()
        pg = PolicyGuesser(network)
        pg.get_loadbalancing_policies(test_policies, fwd_graphs, dom_graphs, simple=True, node_local_reachability=False)

        self.assertCountEqual(test_policies, correct_policies)

    def test_get_waypoint_policies(self):

        network, fwd_graphs, dom_graphs, policy_destination, reachability_policies = self.get_disconnected_network()

        correct_policies = [
            (PolicyType.Waypoint, policy_destination, "r2", PolicySource("r2")),
            (PolicyType.Waypoint, policy_destination, "r2", PolicySource("r3")),
        ]

        test_policies = list()
        pg = PolicyGuesser(network, waypoints=["r2", "r6"])
        pg.get_waypoint_policies(test_policies, fwd_graphs, dom_graphs, node_local_reachability=False)

        self.assertCountEqual(test_policies, correct_policies)

    def test_get_waypoint_policies_simple(self):
        network, fwd_graphs, dom_graphs, policy_destination, _ = self.get_simple_network()

        correct_policies = [
            (PolicyType.Reachability, policy_destination, 0, PolicySource("r2")),
            (PolicyType.Reachability, policy_destination, 0, PolicySource("r3")),
            (PolicyType.Reachability, policy_destination, 0, PolicySource("r4")),
            (PolicyType.Reachability, policy_destination, 0, PolicySource("r5")),
            (PolicyType.Reachability, policy_destination, 0, PolicySource("r6")),
        ]

        test_policies = list()
        pg = PolicyGuesser(network)
        pg.get_reachability_policies(test_policies, fwd_graphs, dom_graphs, node_local_reachability=False)

        self.assertCountEqual(test_policies, correct_policies)


if __name__ == "__main__":
    unittest.main()
