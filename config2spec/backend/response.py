#!/usr/bin/env python
# Author: Ruediger Birkner (Networked Systems Group at ETH Zurich)

import re
import sys

from config2spec.netenv.network_environment import ConcreteEnvironment
from config2spec.policies.policy_db import PolicyStatus
from config2spec.topology.links import Link
from config2spec.utils.logger import get_logger


class Response(object):
    def __init__(self, query, ms_response, debug=False):
        self.logger = get_logger('Response', 'DEBUG' if debug else 'INFO')

        self.type = query.type
        self.sources = query.sources
        self.destination = query.destination
        self.subnet = query.destination.subnet
        self.specifics = query.specifics
        self.netenv = query.environment

        self.counter_example = None
        self.result = list()

        self.parse_response(ms_response)

    def __str__(self):
        if self.counter_example:
            output = "Counter Example: %s\n" % self.counter_example
            output += "Failed Ingresses: %s" % ', '.join([str(src) for i, src in enumerate(self.sources) if self.result[i] == PolicyStatus.HOLDSNOT])
        else:
            output = "Verified"

        return output

    def parse_response(self, response):
        router_to_source = dict()
        for source in self.sources:
            router_to_source[source.router] = source

        # extract counter example from output
        if response.startswith("Verified"):
            # everything holds, so also no counter-example

            self.result = [PolicyStatus.HOLDS] * len(self.sources)
            self.counter_example = None

        else:

            if response.startswith("Flow:"):
                failed_links, source_routers = self.parse_flow_counterexample(response)

            elif response.startswith("Counterexample"):
                failed_links, source_routers = self.parse_generic_counterexample(response)

            else:
                self.logger.error("Unknown response: {response}".format(response=response))
                sys.exit(1)

            self.counter_example = ConcreteEnvironment.from_failed_links(self.netenv.links, failed_links)
            assert len(source_routers) > 0

            ingresses = set()
            for src_router in source_routers:
                if src_router in router_to_source:
                    ingresses.add(router_to_source[src_router])
                else:
                    self.logger.error("We couldn't find an ingress or it didn't match any source...")

            for source in self.sources:
                self.result.append(PolicyStatus.HOLDSNOT if source in ingresses else PolicyStatus.UNKNOWN)

    @staticmethod
    def parse_flow_counterexample(message):
        assert message.startswith("Flow:")

        failed_links = set()
        source_routers = set()

        first = True
        for item in re.split('\n\n', message):
            ingress = re.search('ingress:(.+?) vrf:', item)
            if ingress and ingress.group(1):
                source_routers.add(ingress.group(1))

                if first:
                    first = True
                    tmp_blacklist = re.search('edgeBlacklist=\[(.*?)\]', item)
                    if tmp_blacklist:
                        blacklist = tmp_blacklist.group(1)
                        edges = re.findall('<(.+?):(.+?),\s(.+?):(.+?)>', blacklist)

                        for router1, intf1, router2, intf2 in edges:
                            failed_links.add(Link.get_name(router1, router2))

        return failed_links, source_routers

    @staticmethod
    def parse_generic_counterexample(message):
        assert message.startswith("Counterexample")

        failed_links = set()
        source_routers = set()

        edges = re.findall('link\((.+?),(.+?)\)', message)
        for router1, router2 in edges:
            failed_links.add(Link.get_name(router1, router2))

        return failed_links, source_routers

    def all_hold(self):
        return all(status == PolicyStatus.HOLDS for status in self.result)

    def holds_not(self):
        sources = list()
        for i, source in enumerate(self.sources):
            if self.result[i] == PolicyStatus.HOLDSNOT:
                sources.append(source)
        return sources

    def holds(self):
        sources = list()
        for i, source in enumerate(self.sources):
            if self.result[i] == PolicyStatus.HOLDS:
                sources.append(source)
        return sources
