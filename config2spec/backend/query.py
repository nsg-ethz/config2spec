#!/usr/bin/env python
# Author: Ruediger Birkner (Networked Systems Group at ETH Zurich)

from config2spec.policies.policy import PolicyType


class Query(object):
    def __init__(self, query_type, sources, destination, specifics, environment, negate=False):
        self.type = query_type
        self.str_type = ""
        self.sources = sources

        if isinstance(destination, set):
            self.destination = list(destination)[0]
        else:
            self.destination = destination

        self.specifics = specifics

        self.environment = environment
        self.negate = negate

        self.attributes = dict()
        self.init()

    def init(self):
        if self.type == PolicyType.Reachability:
            self.str_type = "reachability"
            negate = False
        elif self.type == PolicyType.Isolation:
            self.str_type = "reachability"
            negate = True
        elif self.type == PolicyType.Waypoint:
            self.str_type = "waypoint"
            negate = False
        elif self.type == PolicyType.LoadBalancingSimple:
            self.str_type = "loadbalancing"
            negate = False
        elif self.type == PolicyType.LoadBalancingNodeDisjoint:
            self.str_type = "nodedisjointlb"
            negate = False
        else:
            return

        source_str = "|".join(["^{source}$".format(source=source) for source in self.sources])
        self.attributes["IngressNodeRegex"] = source_str
        self.attributes["FinalNodeRegex"] = self.destination.router
        self.attributes["FinalIfaceRegex"] = self.destination.interface
        self.attributes["Negate"] = self.negate != negate
        self.attributes["MaxFailures"] = self.environment.k_failures
        self.attributes["Environment"] = self.environment.get_polish_notation()

        # add policy specific features
        if self.type == PolicyType.Waypoint:
            if isinstance(self.specifics, list):
                self.attributes["Waypoints"] = ",".join(self.specifics)
            else:
                self.attributes["Waypoints"] = self.specifics
        elif self.type == PolicyType.LoadBalancingSimple or self.type == PolicyType.LoadBalancingNodeDisjoint:
            self.attributes["NumPaths"] = self.specifics

    def to_dict(self):
        output = self.attributes.copy()
        output["type"] = self.type

        return output

    def __str__(self):
        output = "{query_type} Query: \n".format(query_type=self.str_type, )
        for key, value in self.attributes.items():
            output += "\t{key}: {value}\n".format(key=key, value=value)
        return output

    def to_string_representation(self):
        output = "Type:{query_type};".format(query_type=self.str_type)
        for key, value in self.attributes.items():
            output += "{key}:{value};".format(key=key, value=value)
        return output
