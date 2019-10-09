#!/usr/bin/env python
# Author: Ruediger Birkner (Networked Systems Group at ETH Zurich)

from enum import Enum


class LinkState(Enum):
    SYMBOLIC = 1
    UP = 2
    DOWN = 3


class Link(object):
    def __init__(self, link_id, edge, state=LinkState.SYMBOLIC):
        self.id = link_id
        self.name = Link.get_name(edge[0], edge[1])
        self.edge = edge
        self.state = state

    def __str__(self):
        return '%s (%s): %s' % (self.id, self.name, self.state)

    def __eq__(self, other):
        if not isinstance(other, Link):
            return False
        return (self.id, self.name, self.edge, self.state) == (other.id, other.name, other.edge, other.state)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __copy__(self):
        return Link(self.id, self.edge, self.state)

    def get_polish_notation(self):
        assert self.state == LinkState.UP or self.state == LinkState.DOWN

        state = 1 if self.state == LinkState.DOWN else 0
        return "= ( {variable} ) ( {state} )".format(variable=self.name, state=state)

    @staticmethod
    def get_name(r1, r2):
        if r1 < r2:
            return "{endpoint1}={endpoint2}".format(endpoint1=r1, endpoint2=r2)
        else:
            return "{endpoint1}={endpoint2}".format(endpoint1=r2, endpoint2=r1)