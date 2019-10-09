#!/usr/bin/env python


from ipaddress import IPv4Network
from pytricia import PyTricia

from config2spec.utils.logger import get_logger


class ForwardingTable(object):
    """
    Builds a trie with all supplied rule prefixes and provides all continuous equivalence classes.
    """
    def __init__(self):
        super(ForwardingTable, self).__init__()

        # initialize logging
        self.logger = get_logger('FECFinder', 'INFO')

        # init Trie
        self.fib = PyTricia()

    def add_entry(self, prefix, interface, route_type, next_hop):
        assert isinstance(prefix, IPv4Network)
        assert next_hop is not None

        fwd_entry = ForwardingTableEntry(prefix, interface, route_type, next_hop)

        if self.fib.has_key(prefix):
            self.fib[prefix].append(fwd_entry)
        else:
            self.fib[prefix] = [fwd_entry]

    def get_next_hop(self, prefix):
        assert isinstance(prefix, IPv4Network)

        next_hops = list()

        if prefix in self.fib:
            entries = self.fib[prefix]

            for entry in entries:
                next_hops.append(entry.next_hop)

        return next_hops

    def get_entries(self, prefix):
        assert isinstance(prefix, IPv4Network)

        if prefix in self.fib:
            entries = self.fib[prefix]
            return entries

        return None


class ForwardingTableEntry(object):
    def __init__(self, prefix, interface, route_type, next_hop):
        self.prefix = prefix
        self.interface = interface
        self.route_type = route_type
        self.next_hop = next_hop

    def __str__(self):
        return "{prefix}: {intf} ({route})".format(prefix=self.prefix, intf=self.interface, route=self.route_type)
