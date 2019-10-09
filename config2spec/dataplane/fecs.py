#!/usr/bin/env python

import socket
import struct

from ipaddress import IPv4Network
from ipaddress import IPv4Address

from config2spec.utils.logger import get_logger


class TrieNode(object):
    def __init__(self, bitstring):
        super(TrieNode, self).__init__()
        self.children = dict()
        self.bitstring = bitstring
        self.is_rule = False


class FECFinder(object):
    """
    Builds a trie with all supplied rule prefixes and provides all continuous equivalence classes.
    """
    def __init__(self):
        super(FECFinder, self).__init__()

        # initialize logging
        self.logger = get_logger('FECFinder', 'INFO')

        # init Trie
        self.root = TrieNode('')
        self.max_depth = 32

        self.prefixes = set()

    def insert_prefix(self, prefix):
        """
        Inserts an IPv4 prefix into the trie
        :param prefix:IPv4 prefix in the form '192.168.1.0/24'
        :return:
        """

        assert isinstance(prefix, IPv4Network)

        if prefix not in self.prefixes:
            self.prefixes.add(prefix)

            bitstring, length = self.ipv4_to_bitstring(prefix)

            current_node = self.root
            for i in range(0, length):
                current_bit = bitstring[i]
                if current_bit in current_node.children:
                    current_node = current_node.children[current_bit]
                else:
                    current_node.children[current_bit] = TrieNode(bitstring[0:i+1])
                    current_node = current_node.children[current_bit]

            current_node.is_rule = True

    def get_all_prefixes(self):
        """
        :return:a list of all rule prefixes currently in the trie
        """
        rules = list()

        stack = [self.root]
        while stack:
            node = stack.pop()

            if node.is_rule:
                prefix = self.bitstring_to_ipv4(node.bitstring)
                rules.append(prefix)

            for child in node.children.values():
                stack.append(child)

        return rules

    def get_all_fecs(self):
        """
        :return:returns a list of all equivalence classes currently in the trie
        """
        fecs = list()

        current_fec = 0
        last_fec = 0

        stack = [(self.root, 0, False)]

        while stack:
            item = stack.pop()

            if isinstance(item[0], TrieNode):
                node, fec, active = item

                # only nodes that are a rule can have no children
                if not node.is_rule and not node.children:
                    self.logger.error('get_all_ecs: "no rule" node without children')
                    continue

                if node.is_rule:
                    last_fec += 1
                    fec = last_fec
                    active = True

                if node.children:
                    bits = ['0', '1']
                    for bit in bits:
                        if bit in node.children:
                            child = node.children[bit]
                            stack.append((child, fec, active))
                        elif active:
                            bitstring = node.bitstring + bit
                            stack.append((bitstring, fec, None))
                else:
                    current_fec = fec
                    tmp_fec = EquivalenceClass()
                    tmp_fec.add_bitstring(node.bitstring)
                    fecs.append(tmp_fec)

            else:
                prefix, fec, _ = item
                if not fecs or fec != current_fec:
                    current_fec = fec
                    fecs.append(EquivalenceClass())

                fecs[-1].add_bitstring(prefix)

        return fecs

    def bitstring_to_ipv4(self, bitstring):
        assert isinstance(bitstring, str)
        length = len(bitstring)
        bitstring += '0' * (self.max_depth - length)
        ip = IPv4Address(int(bitstring, 2))
        return IPv4Network("{network}/{prefix_length}".format(network=ip, prefix_length=length))

    def ipv4_to_bitstring(self, prefix):
        assert isinstance(prefix, IPv4Network)
        length = prefix.prefixlen

        first = int(prefix.network_address)
        bitstring = ("{:032b}".format(first))[0:length]
        return bitstring, length


class EquivalenceClass(object):
    """
    An equivalence class is a continuous range of ip address which are handled the same way
    """
    def __init__(self):
        super(EquivalenceClass, self).__init__()

        # initialize logging
        self.logger = get_logger('EquivalenceClass', 'INFO')

        # first and last address of the equivalence class
        self.first = None
        self.last = None

        # maximum number of bits in an address
        self.max_length = 32

        # needed for the iterator to keep track of the current ip address
        self.current = 0

    def __iter__(self):
        self.current = 0
        return self

    def __hash__(self):
        assert self.first is not None
        assert self.last is not None
        return hash((self.first, self.last))

    def add_prefix(self, prefix):
        assert isinstance(prefix, IPv4Network)

        first = int(prefix.network_address)
        last = int(prefix.broadcast_address)

        self.add_range(first, last)

    def add_bitstring(self, bitstring):
        assert isinstance(bitstring, str)

        prefix_length = len(bitstring)
        first_string = bitstring + "0" * (self.max_length - prefix_length)
        last_string = bitstring + "1" * (self.max_length - prefix_length)

        first = int(first_string, 2)
        last = int(last_string, 2)

        self.add_range(first, last)

    def add_range(self, first, last):
        # initialize ec
        if self.first is None and self.last is None:
            self.first = first
            self.last = last
        else:
            # check for overlap/adjacency with ec
            if (first < self.first and last < self.first - 1) or \
                    (first > self.last + 1 and last > self.last):
                raise DisjointECException

            if first < self.first:
                self.first = first

            if last > self.last:
                self.last = last

    def get(self, item=0):
        if not isinstance(item, int):
            raise TypeError
        if item == -1:
            return self.last
        elif 0 <= item <= self.last - self.first:
            return self.first + item
        else:
            raise IndexError

    def get_ip(self, item=0):
        if not isinstance(item, int):
            raise TypeError
        if item == -1:
            ip = self.last
        elif 0 <= item <= self.last - self.first:
            ip = self.first + item
        else:
            # raise IndexError
            ip = self.first
        return IPv4Address(ip)

    def get_prefix(self):
        # returns the full prefix and if this is not possible the very first one
        if self.first is not None and self.last is not None:

            curr_value = self.first
            i = 0
            while curr_value < self.last and self.first & 1 << i == 0:
                i += 1
                curr_value = curr_value | 1 << i

            prefix_len = 32 - i

            return IPv4Network("{network}/{prefix_length}".format(network=self.get_ip(), prefix_length=prefix_len))
        return None

    def get_all_prefixes(self):
        prefixes = list()

        curr_value = self.first
        while curr_value <= self.last:
            i = 0
            start_value = curr_value
            while curr_value < self.last and start_value & 1 << i == 0:
                curr_value |= 1 << i
                i += 1

            prefix_len = 32 - i
            item = start_value - self.first
            prefix = IPv4Network("{network}/{prefix_length}".format(network=self.get_ip(item), prefix_length=prefix_len))
            prefixes.append(prefix)
            curr_value += 1

        return prefixes

    def next(self):
        if not self.first or not self.last or self.current > self.last - self.first:
            raise StopIteration
        else:
            current_item = self.first + self.current
            self.current += 1
            return current_item

    def __str__(self):
        assert self.first is not None
        assert self.last is not None
        first_ip = socket.inet_ntoa(struct.pack('!L', self.first))
        last_ip = socket.inet_ntoa(struct.pack('!L', self.last))
        return "EquivalenceClass({first_ip} - {last_ip})".format(first_ip=first_ip, last_ip=last_ip)

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        if not isinstance(other, EquivalenceClass):
            return False
        return self.first == other.first and self.last == other.last

    def __ne__(self, other):
        return not self.__eq__(other)


class DisjointECException(Exception):
    pass
