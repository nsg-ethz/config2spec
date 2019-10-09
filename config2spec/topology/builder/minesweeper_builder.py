#!/usr/bin/env python
# Author: Ruediger Birkner (Networked Systems Group at ETH Zurich)

import os
import re


from collections import defaultdict


from config2spec.topology.builder.builder import TopologyBuilder
from config2spec.topology.topology import NetworkTopology
from config2spec.topology.interface import Interface
from config2spec.topology.access_list import AccessList
from config2spec.utils.logger import get_logger


# initialize logging
logger = get_logger('ConfigTopologyGenerator', 'INFO')


class BackendTopologyBuilder(TopologyBuilder):
    @staticmethod
    def build_topology(files, scenario_path):
        assert isinstance(files, dict) and "interfaces" in files and "acls" in files and "topology" in files

        interface_path = os.path.join(scenario_path, files["interfaces"])
        all_interfaces = BackendTopologyBuilder.parse_interfaces(interface_path)

        acls_path = os.path.join(scenario_path, files["acls"])
        all_access_lists = BackendTopologyBuilder.parse_acls(acls_path)

        topology_path = os.path.join(scenario_path, files["topology"])
        routers, edges = BackendTopologyBuilder.parse_topology(topology_path)

        topology = NetworkTopology()
        for i, router in enumerate(routers):
            router_id = "r%d" % i
            interfaces, access_lists = all_interfaces[router], all_access_lists[router]
            topology.add_router(router, router_id, interfaces=interfaces, access_lists=access_lists)

        # LINKS maybe use the edge information
        for r1, r1_intf, r2, r2_intf in edges:
            topology.add_link(r1, r2, 1)
            topology.next_hops[r1][r1_intf] = r2

        return topology

    @staticmethod
    def parse_topology(topology_path):
        routers = set()
        edges = set()

        edge_regex = "^<(?P<router1>\S+):(?P<interface1>\S+?)(?:\.(?P<vlan1>[0-9]+))?,\s" \
                     "(?P<router2>\S+):(?P<interface2>\S+?)(?:\.(?P<vlan2>[0-9]+))?>$"

        with open(topology_path, "r") as infile:
            for line in infile:
                edge_match = re.match(edge_regex, line)
                edge_data = edge_match.groupdict()

                routers.add(edge_data["router1"])
                routers.add(edge_data["router2"])

                if "vlan1" in edge_data and edge_data["vlan1"] is not None:
                    intf1 = "%s.%s" % (edge_data["interface1"], edge_data["vlan1"])
                else:
                    intf1 = "%s" % (edge_data["interface1"],)

                if "vlan2" in edge_data and edge_data["vlan2"] is not None:
                    intf2 = "%s.%s" % (edge_data["interface2"], edge_data["vlan2"])
                else:
                    intf2 = "%s" % (edge_data["interface2"],)

                edges.add((edge_data["router1"], intf1, edge_data["router2"], intf2))

        return routers, edges

    @staticmethod
    def parse_interfaces(interface_path):
        interfaces = defaultdict(dict)

        with open(interface_path, "r") as infile:
            router = "unknown"
            intf_name = "unknown"
            interface = None

            for line in infile:
                if line.startswith("# Router:"):
                    router = line.strip().split(":")[1]
                elif line.startswith("## Interface:"):
                    intf_regex = "^## Interface:(?P<name>\S+?)(?:\.(?P<sub_id>[0-9]+))?" \
                                 "(?:;IN:(?P<in_acl>\S+?))?(?:;OUT:(?P<out_acl>\S+?))?$"
                    intf_match = re.match(intf_regex, line)
                    intf_data = intf_match.groupdict()

                    if "sub_id" in intf_data and intf_data["sub_id"] is not None:
                        intf_name = "%s.%s" % (intf_data["name"], intf_data["sub_id"])
                    else:
                        intf_name = "%s" % (intf_data["name"], )

                    interface = Interface(intf_name)

                    if "in_acl" in intf_data:
                        interface.set_access_group(intf_data["in_acl"], "in")
                    if "out_acl" in intf_data:
                        interface.set_access_group(intf_data["out_acl"], "out")

                else:
                    ip_regex = "^(?P<ip>[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})\/(?P<prefix_len>[0-9]{1,2})$"
                    ip_match = re.match(ip_regex, line)
                    ip_data = ip_match.groupdict()

                    if intf_name not in interfaces[router]:
                        interfaces[router][intf_name] = interface

                    subnet = "{network}/{prefix_len}".format(network=ip_data["ip"], prefix_len=ip_data["prefix_len"])
                    interfaces[router][intf_name].set_ip_address(ip_data["ip"], subnet)

        return interfaces

    @staticmethod
    def parse_acls(acls_path):
        access_lists = defaultdict(dict)

        with open(acls_path, "r") as infile:
            router = "unknown"
            for line in infile:
                if line.startswith("# Router:"):
                    router = line.strip().split(":")[1]
                else:
                    ip_regex = "[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}"

                    acl_regex = ("^(?P<name>\S+):(?P<type>deny|permit)\sip\s"
                                 "(?P<source>any|{ip_regex}\s{ip_regex})\s"
                                 "(?P<destination>any|{ip_regex}\s{ip_regex})$".format(ip_regex=ip_regex))

                    acl_match = re.match(acl_regex, line)
                    acl_data = acl_match.groupdict()

                    source = TopologyBuilder.get_prefix(acl_data["source"])
                    destination = TopologyBuilder.get_prefix(acl_data["destination"])

                    if acl_data["name"] not in access_lists:
                        access_lists[router][acl_data["name"]] = AccessList(acl_data["name"])

                    if acl_data["type"] == "deny":
                        access_lists[router][acl_data["name"]].add_deny(source, destination)
                    else:
                        access_lists[router][acl_data["name"]].add_permit(source, destination)

        return access_lists
