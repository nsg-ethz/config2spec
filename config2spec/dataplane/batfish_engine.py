#!/usr/bin/env python
# Author: Ruediger Birkner (Networked Systems Group at ETH Zurich)

import networkx as nx
import os
import re
import sys
from collections import defaultdict
from ipaddress import IPv4Network

from config2spec.utils.logger import get_logger
from config2spec.dataplane.fecs import FECFinder
from config2spec.dataplane.fib import ForwardingTable


# Network topology that relies on Batfish for the dataplane computation and
# simply parses the FIB files produced by Batfish.


class BatfishEngine(object):
    def __init__(self, nodes, next_hops, simple_acls, fib_path, debug=False):
        self.debug = debug
        self.logger = get_logger("BatfishEngine", "DEBUG" if debug else "INFO")

        # topology information
        self.nodes = nodes
        self.next_hops = next_hops
        self.simple_acls = simple_acls

        self.forwarding_graphs = defaultdict(nx.DiGraph)
        self.dominator_graphs = defaultdict(nx.DiGraph)

        # path to the directory where batfish writes the FIBs to
        self.fib_path = fib_path

    def get_forwarding_graphs(self, fib_file_name, vrf="default"):

        fib_file = os.path.join(self.fib_path, fib_file_name)

        self.logger.debug("Read FIBs from {fibs}.".format(fibs=fib_file))

        fibs, fecs = self.read_fib_file(fib_file, vrf)

        # build forwarding graphs from FIBS
        self.forwarding_graphs = defaultdict(nx.DiGraph)

        for fec in fecs:
            prefix = fec.get_prefix()

            if prefix in self.simple_acls:
                blocked_edges = self.simple_acls[prefix]
            else:
                blocked_edges = None

            fwd_graph = self.build_forwarding_graph(prefix, blocked_edges, fibs)

            if fwd_graph.edges:
                self.forwarding_graphs[prefix] = fwd_graph
            else:
                self.logger.debug("No forwarding graph for {fec} - {prefix}".format(fec=fec, prefix=prefix))

        if self.debug:
            self.logger.debug(self.debug_output())

        return self.forwarding_graphs

    def read_fib_file(self, fib_file, vrf="default"):

        fec_finder = FECFinder()
        fibs = defaultdict(ForwardingTable)

        with open(fib_file, "r") as infile:
            router = "unknown"
            current_vrf = "unknown"

            for line in infile:
                line = line.strip()

                if line.startswith("# "):
                    router_match = re.match("^# Router:([a-zA-Z0-9\-_&]+)$", line)
                    router = router_match.group(1) if router_match else "unknown"

                elif line.startswith("## "):
                    vrf_match = re.match("^## VRF:([a-zA-Z0-9\-]+)$", line)
                    current_vrf = vrf_match.group(1) if vrf_match else "unknown"

                elif current_vrf == vrf:
                    # only keep forwarding entries if they belong to the VRF under investigation
                    raw_prefix, interface, route_type = line.split(';')

                    # keep track of all prefixes to later compute all forwarding equivalence classes
                    prefix = IPv4Network(raw_prefix)
                    fec_finder.insert_prefix(prefix)

                    # set next hop as sink if it is a directly connected route
                    if route_type == "ConnectedRoute":
                        next_hop = "sink"
                    # don't do anything if route points to the null interface (blackholed)
                    elif interface == "null_interface":
                        continue
                    elif router in self.next_hops and interface in self.next_hops[router]:
                        next_hop = self.next_hops[router][interface]
                    else:
                        self.logger.error("Prefix: {prefix} - Unknown interface {intf} or "
                                          "router {router}.".format(prefix=prefix, intf=interface, router=router))
                        next_hop = "external"
                        # sys.exit(1)

                    # add entry to forwarding table
                    fibs[router].add_entry(prefix, interface, route_type, next_hop)

        # get all forwarding equivalence classes
        fecs = fec_finder.get_all_fecs()

        return fibs, fecs

    def build_forwarding_graph(self, prefix, blocked_edges, fibs):
        """

        :param prefix: IPv4Network object of the prefix
        :param simple_acls: List of edges (tuples of endpoints) on which traffic to that prefix is dropped
        :param fibs: dict mapping router to ForwardingTable object
        :return: directed graph
        """
        forwarding_graph = nx.DiGraph()

        self.logger.debug("Building forwarding graph for network: {network}".format(network=prefix))

        for router in self.nodes:
            # add all nodes to the forwarding graph
            forwarding_graph.add_node(router)

            # get next hop and add to the forwarding graph
            next_hop_routers = fibs[router].get_next_hop(prefix)
            if next_hop_routers:
                for next_hop_router in next_hop_routers:
                    forwarding_graph.add_edge(router, next_hop_router)
            else:
                self.logger.debug("No path from router {router} to {prefix}.".format(
                    router=router, prefix=prefix))

        # remove edges that are blocked by ACLs
        if blocked_edges:
            for r1, r2 in blocked_edges:
                self.logger.debug("Trying to remove {src}->{dst} for {prefix}".format(src=r1, dst=r2, prefix=prefix))
                if forwarding_graph.has_edge(r1, r2):
                    forwarding_graph.remove_edge(r1, r2)

        return forwarding_graph

    def get_dominator_graphs(self):
        assert self.forwarding_graphs, "Forwarding Graph needs to be built before the Dominator Graphs"

        for subnet, forwarding_graph in self.forwarding_graphs.items():
            rev_graph = forwarding_graph.reverse(copy=True)

            try:
                dominators = set(nx.immediate_dominators(rev_graph, 'sink').items())
            except nx.NetworkXError as e:
                self.logger.error("Sink node is not in the forwarding graph for {subnet}. "
                                  "Official error message: {error}".format(subnet=subnet, error=e))
                # sys.exit(1)
            else:

                if ("sink", "sink") in dominators:
                    dominators.remove(("sink", "sink"))

                tmp_dominator_graph = nx.DiGraph(list(dominators))
                self.dominator_graphs[subnet] = tmp_dominator_graph

        return self.dominator_graphs

    def debug_output(self):
        output = '\n'

        if self.forwarding_graphs:
            for dst, fwd_graph in self.forwarding_graphs.items():
                output += "Forwarding Graph for {dst_subnet}:\n\t".format(dst_subnet=dst)
                output += "\n\t".join("{endpoint1}->{endpoint2}".format(
                    endpoint1=edge[0], endpoint2=edge[1]) for edge in fwd_graph.edges)
                output += "\n\n"
        else:
            output += "No Forwarding Graphs available!\n\n"

        return output
