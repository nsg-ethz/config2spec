#!/usr/bin/env python
# Author: Ruediger Birkner (Networked Systems Group at ETH Zurich)

import copy


from config2spec.topology.links import Link
from config2spec.topology.links import LinkState
from config2spec.netenv.combination_helper import nth_combination
from config2spec.netenv.combination_helper import map_item_to_index
from config2spec.netenv.combination_helper import num_items


class NetworkEnvironment(object):
    def __init__(self, links, k_failures=-1, debug=False):
        self.debug = debug

        self.links = dict()
        self.symbolic_links = list()

        for link in links:
            assert isinstance(link, Link)
            new_link = copy.copy(link)
            self.links[new_link.name] = new_link

        self.num_concrete_envs = 0

        self._k_failures = k_failures

        self.update_env_count()

    def __str__(self):
        output = "NetworkEnvironment with up to {k} failures:\n\t".format(k=self.k_failures)
        output += "\n\t".join(str(link) for link in self.links.values())
        return output

    def __eq__(self, other):
        if not isinstance(other, NetworkEnvironment):
            return False
        return set(self.links) == set(other.links) and self.k_failures == other.k_failures

    def __ne__(self, other):
        return not self.__eq__(other)

    @property
    def k_failures(self):
        # limit the number of possible failures by the number of symbolic links
        if self._k_failures < 0:
            return len(self.links)
        else:
            return self._k_failures

    @k_failures.setter
    def k_failures(self, k):
        self._k_failures = k
        self.update_env_count()

    def set_link(self, name, state):
        assert name in self.links, "Unknown link: {link}".format(link=name)
        assert isinstance(state, LinkState)

        self.links[name].state = state

        self.update_env_count()

    def update_env_count(self):
        self.symbolic_links = list()

        for link in self.links.values():
            if link.state == LinkState.SYMBOLIC:
                self.symbolic_links.append(link.name)

        self.symbolic_links.sort()
        self.num_concrete_envs = num_items(len(self.symbolic_links), self.k_failures)

    def get_polish_notation(self):
        output = ''
        for link in sorted(self.links.values(), key=lambda l: l.name):
            if link.state != LinkState.SYMBOLIC:
                if not output:
                    output = "( {link} )".format(link=link.get_polish_notation(), )
                else:
                    output = "( AND {prev_links} ( {link} ) )".format(
                        prev_links=output, link=link.get_polish_notation(), )
        return output

    def get_concrete_env(self, item):
        assert 0 <= item < self.num_concrete_envs

        index, k_failures = map_item_to_index(item, len(self.symbolic_links), self.k_failures)

        # get combination
        failed_links = nth_combination(index, len(self.symbolic_links), k_failures)

        # create concrete env
        links = list(self.links.values())
        env = ConcreteEnvironment(links)

        # set link states accordingly
        for i, link in enumerate(self.symbolic_links):
                if i in failed_links:
                    env.set_link(link, LinkState.DOWN)
                else:
                    env.set_link(link, LinkState.UP)
        return env


class ConcreteEnvironment(object):
    def __init__(self, links):
        if isinstance(links, dict):
            links = list(links.values())

        assert isinstance(links, list)

        self.links = dict()
        for link in links:
            assert isinstance(link, Link)
            new_link = copy.copy(link)
            self.links[new_link.name] = new_link

    def __str__(self):
        output = "ConcreteEnvironment:\n\t"
        output += "\n\t".join(str(link) for link in self.links.values())
        return output

    def __eq__(self, other):
        if not isinstance(other, ConcreteEnvironment):
            return False

        name_match = set(self.links.keys()) == set(other.links.keys())
        link_match = sorted(self.links.values(), key=lambda l: l.id) == sorted(other.links.values(), key=lambda l: l.id)

        return name_match and link_match

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.__str__())

    def set_link(self, name, state):
        assert name in self.links
        assert isinstance(state, LinkState) and (state == LinkState.DOWN or state == LinkState.UP)

        self.links[name].state = state

    def get_polish_notation(self):
        output = ''
        for link in sorted(self.links.values(), key=lambda l: l.name):
            assert (link.state == LinkState.DOWN or link.state == LinkState.UP)

            if not output:
                output = "( {link} )".format(link=link.get_polish_notation(), )
            else:
                output = "( AND {prev_links} ( {link} ) )".format(
                    prev_links=output, link=link.get_polish_notation(), )
        return output

    def get_links(self, state):
        assert isinstance(state, LinkState)

        links = list()
        for link in self.links.values():
            if link.state == state:
                links.append(link)

        return links

    @staticmethod
    def from_failed_links(links, failed_link_names):
        env = ConcreteEnvironment(links)

        for link_name in env.links.keys():
            if link_name in failed_link_names:
                env.set_link(link_name, LinkState.DOWN)
            else:
                env.set_link(link_name, LinkState.UP)

        return env
