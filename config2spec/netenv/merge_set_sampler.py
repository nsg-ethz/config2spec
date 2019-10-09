#!/usr/bin/env python
# Author: Ruediger Birkner (Networked Systems Group at ETH Zurich)

import networkx as nx
import random

from config2spec.netenv.network_environment import ConcreteEnvironment
from config2spec.netenv.sampler import Sampler
from config2spec.policies.policy_db import PolicyStatus
from config2spec.topology.links import Link
from config2spec.topology.links import LinkState


class MergePolicySetSampler(Sampler):
    def __init__(self, netenv, policy_db, max_num_samples=None, seed=None, use_provided_samples=False, debug=False):
        super(MergePolicySetSampler, self).__init__(netenv, max_num_samples, seed, use_provided_samples, True, debug)

        self.policy_db = policy_db

        self.links = list(self.netenv.links.values())
        self.graph = nx.Graph()
        for link in self.links:
            self.graph.add_edge(link.edge[0], link.edge[1], policies=set())

        self.last_sample = None

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

        # debug output
        if self.debug:
            output = "Weighted Graph:\n"
            for r1, r2, policies in self.graph.edges.data("policies"):
                # output += "\t{link} - {policies}\n".format(link=Link.get_name(r1, r2), policies=policies)
                output += "\t{link} - num policies: {policies}\n".format(link=Link.get_name(r1, r2),
                                                                         policies=len(policies))
            self.logger.debug(output)

        # pick links to fail according to the policies they carry - if we pick an environment that we have used before,
        # we try to merge the previous environment (which lead us to choose the already used one) and the already
        # used one to produce a new one.
        tries = 0
        while True:
            tries += 1

            output = ""
            failed_links = list()

            # order the links by the number of policies they "carry"
            covered_policies = set()
            while len(failed_links) < self.netenv.k_failures:
                all_edges = sorted(self.graph.edges.data("policies"),
                                   key=lambda x: len(x[2].difference(covered_policies)), reverse=True)

                r1, r2, policies = all_edges[0]
                link = Link.get_name(r1, r2)
                failed_links.append(link)
                covered_policies |= policies
                output += "\t{link} - {weight}\n".format(link=Link.get_name(r1, r2), weight=len(policies))

            self.logger.debug("Link choice:\n{links}".format(links=output))

            concrete_env = ConcreteEnvironment.from_failed_links(self.links, failed_links)

            # check if we have already used that specific environment
            if self.use_env(concrete_env):
                self.last_sample = concrete_env
                return concrete_env
            elif tries > 100:
                self.logger.debug("Couldn't find an unused environment and hence, stop here.")
                return None
            else:
                self.logger.debug("We have already used that environment :( Will try to find a new one...")
                links1 = set(link.name for link in self.last_sample.get_links(LinkState.DOWN))
                links2 = set(failed_links)

                # this only works if k is strictly larger than 1 - Hence if k is 0 or 1, there is no other option than
                # to stop here as we cannot merge anything.
                if self.netenv.k_failures <= 1:
                    return None

                failed_links = list()
                failed_links.append(random.choice(list(links1)))
                failed_links.append(random.choice(list(links2)))

                if self.netenv.k_failures - len(failed_links) > 0:
                    union = list(links1.union(links2))
                    additional_links = random.sample(union, self.netenv.k_failures - len(failed_links))
                    failed_links.extend(additional_links)

                output = ""
                for link in failed_links:
                    output += "\t{link}\n".format(link=link)
                self.logger.debug("Link choice:\n{links}".format(links=output))

                concrete_env = ConcreteEnvironment.from_failed_links(self.links, failed_links)

                if self.use_env(concrete_env):
                    self.last_sample = concrete_env
                    return concrete_env
