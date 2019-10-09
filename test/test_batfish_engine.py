#!/usr/bin/env python
# Author: Ruediger Birkner (Networked Systems Group at ETH Zurich)

from ipaddress import IPv4Network
import random
import unittest


from config2spec.dataplane.fib import ForwardingTable
from config2spec.dataplane.batfish_engine import BatfishEngine


class BatfishEngineTest(unittest.TestCase):
    def random_graph(self):
        prefix = IPv4Network("10.0.0.0/8")
        edges = set()
        nodes = list()
        fibs = dict()

        sink = False

        for i in range(0, 10):
            r_id = "r{id}".format(id=i)
            nodes.append(r_id)
            fibs[r_id] = ForwardingTable()

            num_neighbors = random.randint(0, 3)
            for j in random.sample(list(range(0,10)), num_neighbors):
                if j != i:
                    n_id = "r{id}".format(id=j)

                    if (r_id, n_id) not in edges:
                        fibs[r_id].add_entry(prefix, "FastEthernet0/0", "OSPFRouter", n_id)
                        edges.add((r_id, n_id))

                    if not sink:
                        sink = True
                        fibs[r_id].add_entry(prefix, "FastEthernet0/0", "OSPFRouter", "sink")
                        edges.add((r_id, "sink"))

        simple_acls = list()
        for _ in range(0, random.randint(0, 5)):
            i1, i2 = random.sample(list(range(0, 10)), 2)
            r_id1 = "r{id}".format(id=i1)
            r_id2 = "r{id}".format(id=i2)

            simple_acls.append((r_id1, r_id2))

            if (r_id1, r_id2) in edges:
                edges.remove((r_id1, r_id2))

        return prefix, nodes, fibs, simple_acls, list(edges)

    def simple_graph(self):
        prefix = IPv4Network("19.89.12.0/24")
        edges = set()
        nodes = list()
        fibs = dict()

        adj_table = {
            "r1": ["sink", ],
            "r2": [],
            "r3": ["r6", ],
            "r4": ["r2", ],
            "r5": ["r1", ],
            "r6": ["r2", ],
            "r7": ["r5", ],
            "r8": ["r5", "r1"],
        }

        for r_id, adjs in adj_table.items():
            nodes.append(r_id)
            fibs[r_id] = ForwardingTable()

            for n_id in adjs:
                if (r_id, n_id) not in edges:
                    fibs[r_id].add_entry(prefix, "FastEthernet0/0", "OSPFRouter", n_id)
                    edges.add((r_id, n_id))

        simple_acls = list()
        for r_id1, r_id2 in [("r2", "r6"), ]:
            simple_acls.append((r_id1, r_id2))
            if (r_id1, r_id2) in edges:
                edges.remove((r_id1, r_id2))

        # according to the definition in https://en.wikipedia.org/wiki/Dominator_(graph_theory)
        dom_edges = [("r1", "sink"), ("r5", "r1"), ("r8", "r1"), ("r7", "r5")]

        return prefix, nodes, fibs, simple_acls, list(edges), dom_edges

    def test_build_forwarding_graph_random(self):
        for _ in range(0, 100):
            prefix, nodes, fibs, simple_acls, edges = self.random_graph()
            bf_engine = BatfishEngine(nodes, None, simple_acls, None)
            forwarding_graph = bf_engine.build_forwarding_graph(prefix, simple_acls, fibs)

            fwd_edges = list(forwarding_graph.edges())
            self.assertCountEqual(edges, fwd_edges)

    def test_build_forwarding_graph_simple(self):
        prefix, nodes, fibs, simple_acls, edges, _ = self.simple_graph()

        bf_engine = BatfishEngine(nodes, None, simple_acls, None)
        forwarding_graph = bf_engine.build_forwarding_graph(prefix, simple_acls, fibs)

        fwd_edges = list(forwarding_graph.edges())

        self.assertCountEqual(edges, fwd_edges)

    def test_get_dominator_graph(self):
        prefix, nodes, fibs, simple_acls, edges, dom_edges = self.simple_graph()

        bf_engine = BatfishEngine(nodes, None, simple_acls, None)
        forwarding_graph = bf_engine.build_forwarding_graph(prefix, simple_acls, fibs)

        bf_engine.forwarding_graphs[prefix] = forwarding_graph
        dominator_graph = bf_engine.get_dominator_graphs()
        edges = list(dominator_graph[prefix].edges())

        self.assertCountEqual(dom_edges, edges)

if __name__ == "__main__":
    unittest.main()
