#!/usr/bin/env python
# Author: Ruediger Birkner (Networked Systems Group at ETH Zurich)


class Router(object):
    def __init__(self, name, id, interfaces=None, access_lists=None):
        self.name = name
        self.router_id = id

        self.loopback = None

        self.interfaces = interfaces if interfaces is not None else dict()
        self.access_lists = access_lists if access_lists is not None else dict()

    def add_interface(self, intf_name, interface):
        self.interfaces[intf_name] = interface

    def add_access_list(self, acl_name, access_list):
        self.interfaces[acl_name] = access_list

    def get_interfaces(self):
        return self.interfaces.values()

    def get_config(self):
        config = '!\n'
        config += 'version 12.4\n'
        config += 'service timestamps debug datetime msec\n'
        config += 'service timestamps log datetime msec\n'
        config += 'no service password-encryption\n'
        config += '!\n'
        config += 'hostname %s\n' % (self.name, )
        config += '!\n'
        config += 'boot-start-marker\n'
        config += 'boot-end-marker\n'
        config += '!\n'
        config += 'no aaa new-model\n'
        config += 'memory-size iomem 5\n'
        config += 'ip cef\n'
        config += '!\n'
        config += 'no ip domain lookup\n'
        config += 'ip domain name lab.local\n'
        config += 'ip auth-proxy max-nodata-conns 3\n'
        config += 'ip admission max-nodata-conns 3\n'
        config += '!\n'
        config += 'aaa new-model\n'
        config += 'aaa authentication login privilege-mode\n'
        config += '!\n'

        if self.interfaces:
            for interface in self.interfaces.values():
                config += interface.get_config()
                config += '!\n'

        config += 'router ospf 1\n'

        # if loopback interface exists, use that one as id, else just pick one of the interfaces
        if self.loopback:
            loopback_intf = self.interfaces[self.loopback]
            config += ' router-id %s\n' % (loopback_intf.ip_address, )
        else:
            interface = next(iter(self.interfaces.values()))
            config += ' router-id %s\n' % (interface.ip_address,)

        config += ' redistribute connected subnets\n'
        config += '!\n'
        config += 'ip forward-protocol nd\n'
        config += '!\n'
        config += 'no ip http server\n'
        config += 'no ip http secure-server\n'
        config += '!\n'

        if self.access_lists:
            for access_list in self.access_lists.values():
                config += access_list.get_config()
                config += '!\n'

        config += 'control-plane\n'
        config += '!\n'
        config += 'mgcp behavior g729-variants static-pt\n'
        config += '!\n'
        config += 'gatekeeper\n'
        config += ' shutdown\n'
        config += '!\n'
        config += 'line con 0\n'
        config += ' exec-timeout 0 0\n'
        config += ' privilege level 15\n'
        config += ' logging synchronous\n'
        config += 'line aux 0\n'
        config += ' exec-timeout 0 0\n'
        config += ' privilege level 15\n'
        config += ' logging synchronous\n'
        config += 'line vty 0 4\n'
        config += '!\n'
        config += 'end\n'

        return config
