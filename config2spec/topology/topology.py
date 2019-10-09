#!/usr/bin/env python
# Author: Ruediger Birkner (Networked Systems Group at ETH Zurich)

import networkx as nx
import itertools

from collections import defaultdict

from pytricia import PyTricia

from config2spec.utils.logger import get_logger
from config2spec.topology.router import Router
from config2spec.topology.links import Link
from config2spec.topology.links import LinkState


class NetworkTopology(nx.DiGraph):
    def __init__(self, debug=False):
        super(NetworkTopology, self).__init__()

        # name
        self.name = 'unnamed'

        # initialize logging
        self.debug = debug
        self.logger = get_logger('NetworkTopology', 'DEBUG' if debug else 'INFO')

        # dataplane engine that computes forwarding and dominator graphs
        self.dp_engine = None

        # dict of router name to router
        self.routers = dict()

        # mapping of router and interface to the next hop router
        self.next_hops = defaultdict(dict)

        # dict of all subnets in network to router and interface name directly on that subnet
        self.subnets = defaultdict(PyTricia)

        # dict of dst subnet to edges which are blocked by simple ACLs
        self.simple_acls = PyTricia()

        self.links = list()

    def __str__(self):
        output = '%d nodes, %d edges:\n' % (len(self.nodes), len(self.edges))
        for edge in sorted(self.edges, key=lambda e: e[0]):
            state = self.edges[edge]['state']
            output += '{edge}: {state}'.format(edge=Link.get_name(edge[0], edge[1]),
                                               state='up' if state == LinkState.UP else 'down')
            if 'cost' in self.edges[edge]:
                cost = self.edges[edge]['cost']
                output += ' with cost %d' % (cost, )
            output += '\n'
        return output

    def add_router(self, name, router_id, interfaces=None, access_lists=None, **attributes):
        super(NetworkTopology, self).add_node(name, **attributes)

        # TODO add check that no interface address is used more than once

        self.routers[name] = Router(name, router_id, interfaces, access_lists)

        for interface in interfaces.values():
            self.logger.debug('router name: %s, interface name: %s' % (name, interface.name))

            for subnet in interface.get_subnets():
                if self.subnets[name].has_key(subnet):
                    self.subnets[name][subnet].append((name, interface.name))
                else:
                    self.subnets[name][subnet] = [(name, interface.name)]

    def add_link(self, r1, r2, cost, **attributes):
        """
        Add a directed link between router r1 and r2 with the given cost
        :param r1: name of source router
        :param r2: name of destination router
        :param cost: cost of link as int
        :param attributes:
        :return: None
        """

        if self.has_node(r1) and self.has_node(r2):
            super(NetworkTopology, self).add_edge(r1, r2, cost=cost, state=LinkState.UP, **attributes)
        else:
            self.logger.error('either %s or %s do not exist' % (r1, r2))

    def set_interface(self, src, dst, intf_name):
        self.edges[src, dst]['interface'] = intf_name

    def get_interface(self, src, dst):
        return self.edges[src, dst]['interface']

    def get_all_peers(self):
        tmp_peers = defaultdict(list)

        for node in self.nodes():
            if 'peers' in self.nodes[node]:
                for peer in self.nodes[node]['peers']:
                    tmp_peers[peer.local_preference].append((peer.name, node))

        return tmp_peers

    def get_undirected_edges(self):
        graph = self.to_undirected()
        undirected_edges = graph.edges()
        return tuple(undirected_edges)

    def get_links(self):
        if not self.links:
            for i, edge in enumerate(self.get_undirected_edges()):
                link_id = 'l%d' % i
                self.links.append(Link(link_id, edge))
        return self.links

    def get_dependent_edges(self, src_nodes, dst_node):
        # first, find all nodes that are only connected to two neighbors - any path coming from one neighbor goes to
        # the other one and means that it could also be modeled by a direct edge between the two neighbors
        candidate_nodes = list()
        for node in self.nodes:
            if node not in src_nodes and node != dst_node and self.in_degree(node) == 2 and self.out_degree(node) == 2:
                candidate_nodes.append(node)

        dependent_edges = list()

        while candidate_nodes:
            curr_nodes = [candidate_nodes.pop()]
            curr_edges = set()
            while curr_nodes:
                node = curr_nodes.pop()
                neighbors = self.neighbors(node)

                for neighbor in neighbors:
                    curr_edges.add(Link.get_name(neighbor, node))

                    if neighbor in candidate_nodes:
                        candidate_nodes.remove(neighbor)
                        curr_nodes.append(neighbor)

            dependent_edges.append(list(curr_edges))
        return dependent_edges

    def get_interfaces_for_subnet(self, router, subnet):
        if subnet in self.subnets[router]:
            return self.subnets[router][subnet]
        else:
            return list()

    def get_interfaces(self, router):
        return self.routers[router].get_interfaces()

    def get_k_connected_routers(self, k):
        graph = self.to_undirected()

        components = nx.k_edge_components(graph, k=k)

        k_connected_pairs = set()
        for component in components:
            for r1, r2 in itertools.combinations(component, 2):
                if r1 < r2:
                    k_connected_pairs.add((r1, r2))
                else:
                    k_connected_pairs.add((r2, r1))

        return k_connected_pairs
