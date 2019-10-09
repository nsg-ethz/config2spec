#!/usr/bin/env python
# Author: Ruediger Birkner (Networked Systems Group at ETH Zurich)


from collections import defaultdict

from config2spec.topology.access_list import ACLType
from config2spec.utils.logger import get_logger


# initialize logging
logger = get_logger("TopologyBuilder", "INFO")


class TopologyBuilder(object):
    @staticmethod
    def auto_add_links(topology):
        """
        automatically add links between all router interfaces that are defined on the same subnet. only add a link
        if there are exactly two interfaces on that subnet.
        """
        interface_matching = defaultdict(list)

        for router_name, router in topology.routers.items():
            for intf_name, interface in router.interfaces.items():
                interface_matching[interface.subnet.network].append((router_name, intf_name))

        for subnet, names in interface_matching.items():
            if len(names) == 2:
                r1_name, r1_intf_name = names[0]
                r1_cost = topology.routers[r1_name].interfaces[r1_intf_name].ospf_cost
                r1_in_acl = topology.routers[r1_name].interfaces[r1_intf_name].access_group_in
                r1_out_acl = topology.routers[r1_name].interfaces[r1_intf_name].access_group_out

                r2_name, r2_intf_name = names[1]
                r2_cost = topology.routers[r2_name].interfaces[r2_intf_name].ospf_cost
                r2_in_acl = topology.routers[r2_name].interfaces[r2_intf_name].access_group_in
                r2_out_acl = topology.routers[r2_name].interfaces[r2_intf_name].access_group_out

                logger.debug(
                    "Link from {r1} ({intf1}) to {r2} ({intf2}) "
                    "with cost {cost} and ACL (out {out_acl}, in {in_acl})".format(
                        r1=r1_name, intf1=r1_intf_name, r2=r2_name, intf2=r2_intf_name,
                        cost=r1_cost, out_acl=r1_out_acl, in_acl=r2_in_acl))

                topology.add_link(r1_name, r2_name, r1_cost,
                                  src_intf_name=r1_intf_name,
                                  dst_intf_name=r2_intf_name,
                                  out_acl=r1_out_acl,
                                  in_acl=r2_in_acl)

                topology.next_hops[r1_name][r1_intf_name] = r2_name

                logger.debug(
                    "Link from {r1} ({intf1}) to {r2} ({intf2}) "
                    "with cost {cost} and ACL (out {out_acl}, in {in_acl})".format(
                        r1=r2_name, intf1=r2_intf_name, r2=r1_name, intf2=r1_intf_name,
                        cost=r2_cost, out_acl=r2_out_acl, in_acl=r1_in_acl))

                topology.add_link(r2_name, r1_name, r2_cost,
                                  src_intf_name=r2_intf_name,
                                  dst_intf_name=r1_intf_name,
                                  out_acl=r2_out_acl,
                                  in_acl=r1_in_acl)

                topology.next_hops[r2_name][r2_intf_name] = r1_name

            else:
                logger.debug("Odd number of interfaces defined on the same subnet: "
                             "{num_interfaces} on {subnet}".format(num_interfaces=len(names), subnet=subnet))

        # check for simple ACLs (such that only have a destination prefix set)
        for router_name, router in topology.routers.items():
            for intf_name, interface in router.interfaces.items():
                for i, acl_name in enumerate([interface.access_group_in, interface.access_group_out]):
                    if acl_name:
                        for acl in router.access_lists[acl_name].acl_entries:
                            next_hop = topology.next_hops[router_name][intf_name]
                            if i == 0:
                                edge = (next_hop, router_name)
                            else:
                                edge = (router_name, next_hop)

                            if acl.src_net.prefixlen == 0 and acl.type == ACLType.DENY:
                                prefix = acl.dst_net
                                # TODO how does the matching work? LPM? What if, in the end, we have an order of ACLs
                                # first one that matches matters, prefix length doesn't matter
                                if not topology.simple_acls.has_key(prefix):
                                    topology.simple_acls[prefix] = [edge]
                                else:
                                    topology.simple_acls[prefix].append(edge)

        all_acls = "\n".join(
            "\t{prefix}: {acls}".format(prefix=prefix, acls=topology.simple_acls[prefix])
            for prefix in list(topology.simple_acls))
        logger.debug("Found the following simple ACLs: \n{all_acls}".format(all_acls=all_acls))

    @staticmethod
    def get_prefix(prefix_string):
        if prefix_string == "any":
            prefix = "0.0.0.0/0"
        else:
            network = prefix_string.split()[0]
            subnet_mask = prefix_string.split()[1]
            prefix_len = TopologyBuilder.get_prefix_len(subnet_mask, True)
            prefix = "{network}/{prefix_len}".format(network=network, prefix_len=prefix_len)
        return prefix

    @staticmethod
    def get_prefix_len(subnet_mask, reverse=False):
        str_octets = subnet_mask.split('.')
        int_octets = [int(octet) for octet in str_octets]

        if reverse:
            int_octets = [(255 - octet) for octet in int_octets]

        bin_octets = ["{:08b}".format(octet) for octet in int_octets]
        binary_subnet_mask = ''.join(bin_octets)

        for i in range(len(binary_subnet_mask)):
            if binary_subnet_mask[i] == "0":
                return i
        return 32
