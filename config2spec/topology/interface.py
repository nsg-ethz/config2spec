#!/usr/bin/env python
# Author: Ruediger Birkner (Networked Systems Group at ETH Zurich)

from ipaddress import IPv4Network
from ipaddress import IPv4Address


class Interface(object):
    def __init__(self, name):
        self.name = name
        self.ip_addresses = list()
        self.ospf_cost = 1
        self.access_group_in = None
        self.access_group_out = None

    def set_ip_address(self, ip_address, subnet):
        self.ip_addresses.append(IPAdress(ip_address, subnet))

    def set_ospf_cost(self, cost):
        self.ospf_cost = cost

    def set_access_group(self, access_group, direction):
        if direction == 'in':
            self.access_group_in = access_group
        if direction == 'out':
            self.access_group_out = access_group

    def get_subnets(self):
        subnets = list()
        for ip_address in self.ip_addresses:
            subnets.append(ip_address.subnet)

        return subnets

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        ip_addresses = "\n\t\t".join(str(ip) for ip in self.ip_addresses)

        return 'Interface %s\n\tip addresses: \n\t\t%s\n\tospf cost: %d\n\taccess group - in: %s, out %s' % \
               (self.name, ip_addresses, self.ospf_cost, self.access_group_in, self.access_group_out)

    def get_config(self):
        config = 'interface %s\n' % (self.name, )
        for ip_address in self.ip_addresses:
            config += ' ip address %s %s\n' % (ip_address.ip_address, ip_address.subnet.netmask)

        if self.access_group_in:
            config += ' ip access-group %s in\n' % (self.access_group_in, )
        if self.access_group_out:
            config += ' ip access-group %s out\n' % (self.access_group_out, )
        config += ' ip ospf 1 area 0\n'
        config += ' ip ospf cost %d\n' % (self.ospf_cost, )
        config += ' duplex auto\n'
        config += ' speed auto\n'

        return config


class IPAdress(object):
    def __init__(self, ip_address, ip_network):
        if isinstance(ip_address, IPv4Address):
            self.ip_address = ip_address
        else:
            self.ip_address = IPv4Address(ip_address)

        if isinstance(ip_network, IPv4Network):
            self.subnet = ip_network
        else:
            self.subnet = IPv4Network(ip_network, strict=False)

    def __str__(self):
        return "{} netmask {}".format(self.ip_address, self.subnet.netmask)