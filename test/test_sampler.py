#!/usr/bin/env python
# Author: Ruediger Birkner (Networked Systems Group at ETH Zurich)

import random
import unittest

from config2spec.netenv.sampler import Sampler

from config2spec.topology.links import Link
from config2spec.topology.links import LinkState
from config2spec.netenv.network_environment import NetworkEnvironment
from config2spec.netenv.network_environment import ConcreteEnvironment


class SamplerTest(unittest.TestCase):
    @staticmethod
    def get_random_links():
        links = list()
        symbolic_link_names = list()
        for i in range(1, 15):
            r1 = "r{id}".format(id=i)
            r2 = "r{id}".format(id=i*9)
            state = random.choice([LinkState.UP, LinkState.DOWN, LinkState.SYMBOLIC])
            link = Link("l{id}".format(id=i), (r1, r2), state=state)
            links.append(link)

            if state == LinkState.SYMBOLIC:
                symbolic_link_names.append(link.name)

        max_failures = random.randint(0, len(symbolic_link_names))

        return links, symbolic_link_names, max_failures

    def test_max_num_samples(self):
        for _ in range(0, 1000):
            links, symbolic_link_names, max_failures = SamplerTest.get_random_links()
            netenv = NetworkEnvironment(links, k_failures=max_failures)

            max_num_samples = random.randint(0, 2 * netenv.num_concrete_envs)
            sampler = Sampler(netenv, max_num_samples=max_num_samples)
            correct_max_num_samples = min(max_num_samples, netenv.num_concrete_envs)

            self.assertEqual(sampler.max_num_samples, correct_max_num_samples)

    def test_more_envs(self):
        for _ in range(0, 1000):
            links, symbolic_link_names, max_failures = SamplerTest.get_random_links()
            netenv = NetworkEnvironment(links, k_failures=max_failures)

            max_num_samples = random.randint(0, 2 * netenv.num_concrete_envs)
            sampler = Sampler(netenv, max_num_samples=max_num_samples)
            sampler.used_samples = random.randint(0, max_num_samples)

            correct_more_envs = sampler.used_samples < min(max_num_samples, netenv.num_concrete_envs)

            self.assertEqual(sampler.more_envs(), correct_more_envs)

    def test_use_env(self):
        for _ in range(0, 1000):
            links, symbolic_link_names, max_failures = SamplerTest.get_random_links()
            netenv = NetworkEnvironment(links, k_failures=max_failures)

            sampler = Sampler(netenv)

            used_samples = set()
            for j in range(0, 10):
                sample = random.randint(0, netenv.num_concrete_envs - 1)
                concrete_env = netenv.get_concrete_env(sample)

                self.assertEqual(sampler.use_env(concrete_env), sample not in used_samples)
                used_samples.add(sample)

    def test_get_all_up(self):
        for _ in range(0, 1000):
            links, symbolic_link_names, max_failures = SamplerTest.get_random_links()
            netenv = NetworkEnvironment(links, k_failures=max_failures)

            failed_links = [link.name for link in links if link.state == LinkState.DOWN]
            all_up_env = ConcreteEnvironment.from_failed_links(links, failed_links)

            sampler = Sampler(netenv)

            self.assertEqual(sampler.get_all_up(), all_up_env)


if __name__ == "__main__":
    unittest.main()
