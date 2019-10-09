#!/usr/bin/env python
# Author: Ruediger Birkner (Networked Systems Group at ETH Zurich)

import time

import networkx as nx

from config2spec.policies.policy import PolicyDestination
from config2spec.policies.policy import PolicySource
from config2spec.policies.policy import PolicyType
from config2spec.topology.links import Link

from config2spec.utils.logger import get_logger


class PolicyGuesser(object):
    def __init__(self, network, waypoints=None, debug=False):

        # initialize logging
        self.debug = debug
        self.logger = get_logger("PolicyGuesser", 'DEBUG' if debug else 'INFO')

        # load network
        self.network = network

        # only use waypoints if they are specified by the user
        if not waypoints:
            waypoints = list()
        self.waypoints = waypoints

    def get_policies(self, forwarding_graphs, dominator_graphs, node_local_reachability=False):
        # a policy is a tuple of (PolicyType, Destination, Specifics, Source)
        policies = list()

        # get reachability/isolation policies
        self.get_reachability_policies(policies, forwarding_graphs, dominator_graphs, node_local_reachability=node_local_reachability)
        num_reachability = len(policies)

        # get loadbalancing policies
        self.get_loadbalancing_policies(policies, forwarding_graphs, dominator_graphs, node_local_reachability=node_local_reachability)
        num_loadbalancing = len(policies) - num_reachability

        # get waypoint policies
        num_waypoints = 0
        if self.waypoints:
            self.get_waypoint_policies(policies, forwarding_graphs, dominator_graphs, node_local_reachability=node_local_reachability)
            num_waypoints = len(policies) - num_loadbalancing - num_reachability

        if self.debug:
            self.logger.debug(
                "Found {num_policies} policies: {num_reachability} reachability/isolation, "
                "{num_loadbalancing} loadbalancing, and {num_waypoints} waypoints.".format(
                    num_policies=len(policies), num_reachability=num_reachability,
                    num_loadbalancing=num_loadbalancing, num_waypoints=num_waypoints))

        return policies

    def get_reachability_policies(self, policies, forwarding_graphs, dominator_graphs, node_local_reachability=False):

        all_nodes = set(self.network.nodes())

        # iterate over every forwarding graph and check if it is connected
        start_time = time.time()
        for subnet, graph in dominator_graphs.items():

            all_destinations, destinations, dst_routers = self.get_destination_interfaces_for_subnet(subnet, forwarding_graphs[subnet])

            # only use router specific subnets (e.g., subnets that are connected at a single interface, such as loopback
            # and host subnets). This removes all subnet that just exist between two routers (usually /31)
            if len(all_destinations) > 1 or len(all_destinations) == 0:
                continue

            # get all routers that can reach the destination and all routers that are isolated from it
            reachable_sources = set(graph.nodes())
            isolated_sources = all_nodes.difference(reachable_sources)

            if 'sink' in reachable_sources:
                reachable_sources.remove("sink")

            # prevent policies within a single router (e.g., r1 can reach r1:loopback0)
            if not node_local_reachability:
                for dst_router in dst_routers:
                    reachable_sources.remove(dst_router)

            # add all reachability policies
            for source in reachable_sources:
                policy_source = PolicySource(source)
                policy_destinations = destinations[source]
                for policy_destination in policy_destinations:
                    policies.append((PolicyType.Reachability, policy_destination, 0, policy_source))

            # add all isolation policies
            for source in isolated_sources:
                policy_source = PolicySource(source)
                for policy_destination in all_destinations:
                    policies.append((PolicyType.Isolation, policy_destination, 0, policy_source))

        self.logger.debug(
            "Getting the reachability policies from the forwarding graphs took {time:.4f}s.".format(
                time=time.time()-start_time))

        return policies

    def get_loadbalancing_policies(self, policies, forwarding_graphs, dominator_graphs, node_local_reachability=False,
                                   simple=True, edge_disjoint=False, node_disjoint=False):

        start_time = time.time()
        for subnet, graph in dominator_graphs.items():
            all_destinations, destinations, dst_routers = self.get_destination_interfaces_for_subnet(subnet, forwarding_graphs[subnet])

            # TODO how to deal with Loadbalancing to same prefix, but last hop is different router?!
            # only use router specific subnets (e.g., subnets that are connected at a single interface, such as loopback
            # and host subnets). This removes all subnet that just exist between two routers (usually /31)
            if len(all_destinations) > 1:
                continue

            for node in graph.nodes():
                # prevent policies within the same router
                if node == "sink" or (not node_local_reachability and node in dst_routers):
                    continue

                if len(destinations[node]) == 1:
                    policy_destination = destinations[node][0]
                    dst_router = policy_destination.router
                else:
                    self.logger.error("There should only be a single destination for {node} this subnet: {subnet}.".format(node=node, subnet=subnet))
                    continue

                policy_source = PolicySource(node)

                all_paths = list(nx.all_simple_paths(forwarding_graphs[subnet], node, "sink"))

                # only continue if there is more than one path available
                if len(all_paths) > 1:
                    # simple loadbalancing, more than a single path
                    if simple:
                        policies.append((PolicyType.LoadBalancingSimple, policy_destination, len(all_paths), policy_source))

                    # edge disjoint loadbalancing
                    if edge_disjoint:
                        edge_disjoint_paths = list()
                        edge_union = set()
                        for path in all_paths:
                            edges = set([Link.get_name(path[i], path[i + 1]) for i in range(len(path)-1)])

                            if not edge_union.intersection(edges):
                                edge_union.union(edges)
                                edge_disjoint_paths.append(path)

                        if len(edge_disjoint_paths) > 1:
                            self.logger.debug("There are {num_paths} edge-disjoint paths from {src} to {dst}.".format(
                                num_paths=len(edge_disjoint_paths), src=node, dst=dst_router))

                            # TODO add policies

                    # node disjoint loadbalancing
                    if node_disjoint:
                        node_disjoint_paths = list()
                        node_union = set()
                        for path in all_paths:
                            # need to remove the source and destination as all the paths will have them in common
                            nodes = set(path[1:-1])

                            if not node_union.intersection(nodes):
                                node_union.union(nodes)
                                node_disjoint_paths.append(path)

                        if len(node_disjoint_paths) > 1:
                            self.logger.debug("There are {num_paths} node-disjoint paths from {src} to {dst}.".format(
                                 num_paths=len(node_disjoint_paths), src=node, dst=dst_router))

                            # TODO add policies

        self.logger.debug("Getting the loadbalancing policies from the forwarding graphs took {time:.4f}s.".format(
            time=time.time()-start_time, ))

        return policies

    def get_waypoint_policies(self, policies, forwarding_graphs, dominator_graphs, node_local_reachability=False):

        start_time = time.time()
        for subnet, graph in dominator_graphs.items():

            all_destinations, destinations, dst_routers = self.get_destination_interfaces_for_subnet(subnet, forwarding_graphs[subnet])

            # TODO how to deal with Loadbalancing to same prefix, but last hop is different router?!
            # only use router specific subnets (e.g., subnets that are connected at a single interface, such as loopback
            # and host subnets). This removes all subnet that just exist between two routers (usually /31)
            if len(all_destinations) > 1:
                continue

            for waypoint in self.waypoints:
                if waypoint in graph:
                    candidates = [waypoint]
                    sources = [PolicySource(waypoint)]

                    while candidates:
                        current_node = candidates.pop()
                        if current_node not in graph:
                            self.logger.error(
                                "Node {node} is not in the dominator graph for subnet {subnet}.".format(
                                    node=current_node, subnet=subnet))
                            break
                        predecessors = list(graph.predecessors(current_node))

                        candidates.extend(predecessors)
                        for predecessor in predecessors:

                            # prevent policies within a single router (e.g., r1 can reach r1:loopback0)
                            if not (not node_local_reachability and predecessor in dst_routers):
                                sources.append(PolicySource(predecessor))

                    for source in sources:
                        if source.router not in dst_routers:
                            for policy_destination in destinations[source.router]:
                                policies.append((PolicyType.Waypoint, policy_destination, waypoint, source))

        self.logger.debug("Getting the waypoint policies from dominator and forwarding graph took {time:.4f}s.".format(
            time=time.time()-start_time, ))

        return policies

    def get_destination_interfaces_for_subnet(self, subnet, forwarding_graph):
        dst_routers = set()  # all routers that are directly connected to the sink
        all_destinations = set()
        destinations = dict()

        interfaces = list()
        for router in forwarding_graph.predecessors("sink"):
            interfaces.extend(self.network.get_interfaces_for_subnet(router, subnet))

        for dst_router, dst_interface in interfaces:
            dst_routers.add(dst_router)
            policy_destination = PolicyDestination(dst_router, dst_interface, subnet)
            all_destinations.add(policy_destination)

            for node, _ in nx.single_target_shortest_path_length(forwarding_graph, dst_router):
                if node not in destinations:
                    destinations[node] = [policy_destination]
                else:
                    destinations[node].append(policy_destination)

        return all_destinations, destinations, dst_routers
