#!/usr/bin/env python
# Author: Ruediger Birkner (Networked Systems Group at ETH Zurich)

import unittest

from collections import defaultdict

from config2spec.topology.topology import NetworkTopology
from config2spec.topology.interface import Interface
from config2spec.topology.links import Link


class TopologyTest(unittest.TestCase):
    def setUp(self):
        # adjacency list - (link to itself just represents the subnet/interface to which the hosts are attached
        neighbors = {
            1: [1, 2, 3, 4],
            2: [2, 1, 3],
            3: [3, 1, 2, 4],
            4: [4, 1, 3]
        }

        self.subnet_to_intfs = defaultdict(list)
        self.topology = NetworkTopology()

        # add all routers to the network
        for r_id, neighbor_ids in neighbors.items():
            router_id = "r{}".format(r_id)
            router_name = "r{}".format(r_id)

            interfaces = dict()
            for i, n_id in enumerate(neighbor_ids):
                intf_name = "FastEthernet{}/{}".format(i/2, i%2)
                neighbor_id = "r{}".format(n_id)

                self.topology.next_hops[router_id][intf_name] = neighbor_id

                if i == 0:
                    ip_address = "10.0.{}.1".format(n_id)
                    ip_network = "10.0.{}.0/24".format(n_id)
                elif neighbor_id < router_id:
                    ip_address = "10.{}.{}.2".format(n_id, r_id)
                    ip_network = "10.{}.{}.0/24".format(n_id, r_id)
                else:
                    ip_address = "10.{}.{}.1".format(r_id, n_id)
                    ip_network = "10.{}.{}.0/24".format(r_id, n_id)

                interfaces[intf_name] = Interface(intf_name)
                interfaces[intf_name].set_ip_address(ip_address, ip_network)

                subnets = interfaces[intf_name].get_subnets()
                for subnet in subnets:
                    self.subnet_to_intfs[subnet].append((router_name, intf_name))

            self.topology.add_router(router_name, router_id, interfaces, dict())

        # add the links between the routers
        for r_id, neighbor_ids in neighbors.items():
            for i, n_id in enumerate(neighbor_ids):
                if i > 0:
                    r1_name = "r{}".format(r_id)
                    r2_name = "r{}".format(n_id)
                    self.topology.add_link(r1_name, r2_name, 5)

    def test_get_interfaces_for_subnet(self):
        for subnet, true_intfs in self.subnet_to_intfs.items():
            intfs = list()
            for router in self.topology.nodes():
                intfs.extend(self.topology.get_interfaces_for_subnet(router, subnet))
            self.assertCountEqual(true_intfs, intfs, msg="subnet: {}".format(subnet))

    def test_get_dependent_edges(self):
        router_pairs = [
            ("r1", "r2", [[Link.get_name("r1", "r4"), Link.get_name("r3", "r4")]]),
            ("r1", "r3", [[Link.get_name("r1", "r4"), Link.get_name("r3", "r4")], [Link.get_name("r1", "r2"), Link.get_name("r2", "r3")]]),
            ("r2", "r4", []),
        ]
        for r1, r2, true_dep_edges in router_pairs:
            tmp_dependent_edges = self.topology.get_dependent_edges([r1], r2)
            dependent_edges = [sorted(dep_edges) for dep_edges in tmp_dependent_edges]
            self.assertCountEqual(true_dep_edges, dependent_edges, msg="dependent edges from {} to {}".format(r1, r2))


if __name__ == "__main__":
    unittest.main()