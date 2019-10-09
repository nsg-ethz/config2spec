#!/usr/bin/env python
# Author: Ruediger Birkner (Networked Systems Group at ETH Zurich)

import networkx as nx
import numpy as np

from config2spec.netenv.network_environment import ConcreteEnvironment
from config2spec.netenv.sampler import Sampler
from config2spec.policies.policy_db import PolicyStatus
from config2spec.topology.links import Link


class RandomPolicySetSampler(Sampler):
    def __init__(self, netenv, policy_db, max_num_samples=None, seed=None, use_provided_samples=False, debug=False):
        super(RandomPolicySetSampler, self).__init__(netenv, max_num_samples, seed, use_provided_samples, True, debug)

        self.policy_db = policy_db

        self.links = list(self.netenv.links.values())
        self.graph = nx.Graph()
        for link in self.links:
            self.graph.add_edge(link.edge[0], link.edge[1], policies=set())

    def get_next_env(self, fwd_graphs, provided_env=None):
        # first check if there are any samples left, if not, return None
        if not self.more_envs():
            self.logger.debug("No more states left for sampling")
            return None

        # reset all policies on the edges
        for r1, r2 in self.graph.edges:
            self.graph.edges[r1, r2]['policies'] = set()

        # from the policy db get all destinations and the sources for which we have a policy
        source_counts = self.policy_db.get_source_counts(status=PolicyStatus.UNKNOWN)

        # create a pseudo policy identifier - at the moment, we don't actually care which policy it represents, but
        # just that it represents different policies.
        policy_id = 0

        # augment the weight graph with the policy information
        for subnet, counts in source_counts.items():

            assert subnet in fwd_graphs, "no forwarding graph for {subnet}".format(subnet=subnet)
            fwd_graph = fwd_graphs[subnet]

            for source, counts in counts.items():
                all_paths = nx.all_simple_paths(fwd_graph, source.router, "sink")

                for count in range(counts):
                    policy_id += 1

                    for path in all_paths:
                        for i in range(0, len(path) - 2):
                            self.graph.edges[path[i], path[i + 1]]["policies"].add(policy_id)

        # Debug
        if self.debug:
            output = "Weighted Graph:\n"
            for r1, r2, policies in self.graph.edges.data("policies"):
                # output += "\t{link} - {policies}\n".format(link=Link.get_name(r1, r2), policies=policies)
                output += "\t{link} - num policies: {policies}\n".format(link=Link.get_name(r1, r2),
                                                                         policies=len(policies))
            self.logger.debug(output)

        # Pick the environment - Try at most 100 times
        tries = 0
        while True:
            tries += 1

            output = ""
            failed_links = list()

            # order the links by the number of policies they "carry"
            covered_policies = set()
            for i in range(0, self.netenv.k_failures):
                all_edges = list(self.graph.edges.data("policies"))

                total_weight = 0
                weights = list()
                for r1, r2, policies in all_edges:
                    num_uncovered_policies = len(policies.difference(covered_policies))

                    total_weight += num_uncovered_policies
                    weights.append(float(num_uncovered_policies))

                if total_weight != 0:
                    normalized_weights = [w/total_weight for w in weights]
                    edge_id = np.random.choice(len(all_edges), 1, replace=False, p=normalized_weights)[0]
                else:
                    edge_id = np.random.choice(len(all_edges), 1, replace=False)[0]

                r1, r2, policies = all_edges[edge_id]

                failed_links.append(Link.get_name(r1, r2))
                output += "\t{link} - {weight}\n".format(link=Link.get_name(r1, r2), weight=len(policies))

                covered_policies |= policies

            self.logger.debug("Link choice:\n{links}".format(links=output))

            concrete_env = ConcreteEnvironment.from_failed_links(self.links, failed_links)

            # check if we have already used that specific environment
            if self.use_env(concrete_env):
                return concrete_env
            elif tries > 100:
                self.logger.debug("Couldn't find an unused environment and hence, stop here.")
                return None
