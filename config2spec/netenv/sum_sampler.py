#!/usr/bin/env python
# Author: Ruediger Birkner (Networked Systems Group at ETH Zurich)

import networkx as nx
import numpy as np

from config2spec.netenv.network_environment import ConcreteEnvironment
from config2spec.netenv.sampler import Sampler
from config2spec.policies.policy_db import PolicyStatus
from config2spec.topology.links import Link


class PolicySumSampler(Sampler):
    def __init__(self, netenv, policy_db, max_num_samples=None, seed=None, use_provided_samples=False, debug=False):
        super(PolicySumSampler, self).__init__(netenv, max_num_samples, seed, use_provided_samples, True, debug)

        self.policy_db = policy_db

        self.links = list(self.netenv.links.values())
        self.graph = nx.Graph()
        for link in self.links:
            self.graph.add_edge(link.edge[0], link.edge[1], weight=0)

    def get_next_env(self, fwd_graphs, provided_env=None):
        # first check if there are any samples left, if not, return None
        if not self.more_envs():
            self.logger.debug("No more states left for sampling")
            return None

        # make a copy of the weight graph
        graph = self.graph.copy()

        # from the policy db get all destinations and the sources for which we have a policy
        source_counts = self.policy_db.get_source_counts(status=PolicyStatus.UNKNOWN)

        # augment the weight graph with the policy information
        for subnet, counts in source_counts.items():

            assert subnet in fwd_graphs, "no forwarding graph for {subnet}".format(subnet=subnet)
            fwd_graph = fwd_graphs[subnet]

            for source, count in counts.items():
                all_paths = nx.all_simple_paths(fwd_graph, source.router, "sink")

                for path in all_paths:
                    for i in range(0, len(path) - 2):
                        graph.edges[path[i], path[i + 1]]["weight"] += count

        # order the links by their weight and create the corresponding probability distribution
        all_edges = sorted(graph.edges.data("weight"), key=lambda x: x[2], reverse=True)

        if self.debug:
            output = "Weighted Graph:\n"
            for r1, r2, weight in all_edges:
                output += "\t{link} - {weight}\n".format(link=Link.get_name(r1, r2), weight=weight)
            self.logger.debug(output)

        total_weight = sum(x[2] for x in all_edges)
        if total_weight < 1:
            weights = None
        else:
            weights = [float(x[2])/total_weight for x in all_edges]

        tries = 0
        while True:
            tries += 1

            # find a combination of edges by sampling k edges using the weights
            try:
                edge_candidates = np.random.choice(len(all_edges), self.netenv.k_failures, replace=False, p=weights)
            except ValueError as e:
                self.logger.error("There was an error in picking the samples: {error}".format(error=e))
                edge_candidates = np.random.choice(len(all_edges), self.netenv.k_failures)

            # create concrete environment from the edge candidates
            output = "Link choice:\n"

            failed_links = list()
            for edge_id in edge_candidates:
                r1, r2, weight = all_edges[edge_id]
                failed_links.append(Link.get_name(r1, r2))

                output += "\t{link} - {weight}\n".format(link=Link.get_name(r1, r2), weight=weight)

            self.logger.debug(output)

            concrete_env = ConcreteEnvironment.from_failed_links(self.links, failed_links)

            # check if we have already used that specific environment
            if self.use_env(concrete_env):
                return concrete_env
            elif tries > 100:
                return self.get_next_unused_env()
