#!/usr/bin/env python
# Author: Ruediger Birkner (Networked Systems Group at ETH Zurich)

from ipaddress import IPv4Network

from enum import Enum

from config2spec.utils.logger import get_logger


class AccessList(object):
    def __init__(self, name):
        self.name = name
        self.acl_entries = list()

        # initialize logging
        self.logger = get_logger('AccessList', 'INFO')

    def add_deny(self, str_src_network, str_dst_network):
        self.add_acl_entry(ACLType.DENY, str_src_network, str_dst_network)

    def add_permit(self, str_src_network, str_dst_network):
        self.add_acl_entry(ACLType.PERMIT, str_src_network, str_dst_network)

    def add_acl_entry(self, acl_type, src_network, dst_network):

        if not isinstance(src_network, IPv4Network):
            src_network = IPv4Network(src_network)

        if not isinstance(dst_network, IPv4Network):
            dst_network = IPv4Network(dst_network)

        self.acl_entries.append(ACLEntry(acl_type, src_network, dst_network))

    def pass_through(self, src_network, dst_network):
        # ACL entries are processed in the order in which they occur on the router/in the config

        self.logger.debug('Check if src %s / dst %s is affected by \n\t%s' % (src_network, dst_network, self))

        for acl_entry in self.acl_entries:
            result = acl_entry.apply(src_network, dst_network)

            if result == ACLType.DENY:
                self.logger.debug('blocked')
                return False
            elif result == ACLType.PERMIT:
                self.logger.debug('permitted')
                return True

        self.logger.debug('blocked')
        return False

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        str_acl_entries = '\n\t'.join([str(acl_entry) for acl_entry in self.acl_entries])

        return 'ACL %s\n\t%s' % (self.name, str_acl_entries)

    def get_config(self):
        config = 'ip access-list extended %s\n' % (self.name, )

        for acl_entry in self.acl_entries:
            config += ' %s\n' % (acl_entry.get_config(), )

        # Any ACL has an implicit "deny everything" statement in the end
        # config += ' deny ip any any\n'

        return config


class ACLType(Enum):
    PERMIT = 1
    DENY = 2


class ACLEntry(object):
    def __init__(self, acl_type, src_net, dst_net):
        assert isinstance(acl_type, ACLType)
        assert isinstance(src_net, IPv4Network)
        assert isinstance(dst_net, IPv4Network)

        self.type = acl_type
        self.src_net = src_net
        self.dst_net = dst_net

    def apply(self, src_network, dst_network):
        assert isinstance(src_network, IPv4Network)
        assert isinstance(dst_network, IPv4Network)

        src_match = src_network.network_address in self.src_net and src_network.broadcast_address in self.src_net
        dst_match = dst_network.network_address in self.dst_net and dst_network.broadcast_address in self.dst_net
        if  src_match and dst_match:
            return self.type
        else:
            return None

    def get_config(self):
        acl_type = "permit" if self.type == ACLType.PERMIT else "deny"
        src_net = 'any' if str(self.src_net) == '0.0.0.0/0' else '%s %s' % (self.src_net.network_address, self.src_net.hostmask)
        dst_net = 'any' if str(self.dst_net) == '0.0.0.0/0' else '%s %s' % (self.dst_net.network_address, self.dst_net.hostmask)
        config = '%s ip %s %s' % (acl_type, src_net, dst_net)

        return config

    def __str__(self):
        src_net = 'any' if str(self.src_net) == '0.0.0.0/0' else str(self.src_net)
        dst_net = 'any' if str(self.dst_net) == '0.0.0.0/0' else str(self.dst_net)
        return '%s %s->%s' % (self.type, src_net, dst_net)

    def __repr__(self):
        return self.__str__()
