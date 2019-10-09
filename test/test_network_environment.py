#!/usr/bin/env python
# Author: Ruediger Birkner (Networked Systems Group at ETH Zurich)

import random
import unittest

from config2spec.netenv.combination_helper import map_item_to_index
from config2spec.netenv.combination_helper import nth_combination
from config2spec.netenv.combination_helper import num_items
from config2spec.netenv.network_environment import ConcreteEnvironment
from config2spec.netenv.network_environment import NetworkEnvironment

from config2spec.topology.links import Link
from config2spec.topology.links import LinkState


class NetworkEnvironmentTest(unittest.TestCase):
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

        return links, symbolic_link_names

    def test_get_polish_notation(self):
        for _ in range(0, 50):
            links, symbolic_link_names = NetworkEnvironmentTest.get_random_links()

            env = NetworkEnvironment(links)

            correct_pn = ""
            for link in sorted(links, key=lambda l: l.name):
                if link.state != LinkState.SYMBOLIC:
                    link_pn = link.get_polish_notation()

                    if not correct_pn:
                        correct_pn = "( {link} )".format(link=link_pn, )
                    else:
                        correct_pn = "( AND {prev_links} ( {link} ) )".format(prev_links=correct_pn, link=link_pn, )

            test_pn = env.get_polish_notation()

            self.assertEqual(test_pn, correct_pn)

    def test_get_concrete_env_out_of_range1(self):
        for _ in range(0, 10):
            links, symbolic_link_names = NetworkEnvironmentTest.get_random_links()
            env = NetworkEnvironment(links)
            num_items = 2**len(symbolic_link_names)

            self.assertRaises(AssertionError, env.get_concrete_env, num_items + 5)

    def test_get_concrete_env_out_of_range2(self):
        for _ in range(0, 10):
            links, symbolic_link_names = NetworkEnvironmentTest.get_random_links()
            env = NetworkEnvironment(links, k_failures=5)

            self.assertRaises(AssertionError, env.get_concrete_env, -20)

    def test_get_concrete_env(self):
        for _ in range(0, 1000):
            links, symbolic_link_names = NetworkEnvironmentTest.get_random_links()

            max_failures = random.randint(0, len(symbolic_link_names))
            env = NetworkEnvironment(links, k_failures=max_failures)
            num_items = env.num_concrete_envs

            item = random.randint(0, num_items - 1)

            index, k = map_item_to_index(item, len(symbolic_link_names), max_failures)
            combination = nth_combination(index, len(symbolic_link_names), k)

            correct_cenv = ConcreteEnvironment(links)
            for i, link_name in enumerate(sorted(symbolic_link_names)):
                if i in combination:
                    correct_cenv.set_link(link_name, LinkState.DOWN)
                else:
                    correct_cenv.set_link(link_name, LinkState.UP)

            test_cenv = env.get_concrete_env(item)

            self.assertEqual(test_cenv, correct_cenv)

    def test_update_env_count(self):
        for _ in range(0, 100):
            links, symbolic_link_names = NetworkEnvironmentTest.get_random_links()

            max_failures = random.randint(0, len(symbolic_link_names))
            env = NetworkEnvironment(links, k_failures=max_failures)

            num_concrete_envs = num_items(len(symbolic_link_names), max_failures)
            self.assertEqual(env.num_concrete_envs, num_concrete_envs)
            self.assertEqual(env.k_failures, min(max_failures, len(symbolic_link_names)))

            num_changes = random.randint(1, len(links))
            links_to_change = random.sample(links, num_changes)

            for link in links_to_change:
                if link.name not in symbolic_link_names:
                    env.set_link(link.name, LinkState.SYMBOLIC)
                    symbolic_link_names.append(link.name)

            num_concrete_envs = num_items(len(symbolic_link_names), max_failures)
            self.assertEqual(env.num_concrete_envs, num_concrete_envs)

            max_failures = random.randint(0, len(symbolic_link_names))
            env.k_failures = max_failures
            self.assertEqual(env.k_failures, min(max_failures, len(symbolic_link_names)))

    def test_equality(self):
        for _ in range(0, 100):
            links, symbolic_link_names = NetworkEnvironmentTest.get_random_links()
            max_failures = random.randint(0, len(symbolic_link_names))
            first_env = NetworkEnvironment(links, k_failures=max_failures)

            second_links = [Link(link.id, link.edge, state=link.state) for link in links]
            second_env = NetworkEnvironment(second_links, max_failures)

            self.assertEqual(first_env, second_env)

    def test_non_equality(self):
        for _ in range(0, 100):
            links1, symbolic_link_names1 = NetworkEnvironmentTest.get_random_links()
            max_failures1 = random.randint(0, len(symbolic_link_names1))
            first_env = NetworkEnvironment(links1, k_failures=max_failures1)

            links2, symbolic_link_names2 = self.get_random_links()
            max_failures2 = random.randint(0, len(symbolic_link_names2))
            while max_failures1 == max_failures2:
                max_failures2 = random.randint(0, len(symbolic_link_names2))
            second_env = NetworkEnvironment(links2, k_failures=max_failures2)

            self.assertNotEqual(first_env, second_env)

    def test_equality_type_mismatch(self):
        links, symbolic_link_names = NetworkEnvironmentTest.get_random_links()
        max_failures = random.randint(0, len(symbolic_link_names))
        first_env = NetworkEnvironment(links, k_failures=max_failures)

        second_env = ConcreteEnvironment(links)

        self.assertNotEqual(first_env, second_env)

        self.assertNotEqual(first_env, "Test")

        self.assertNotEqual(first_env, None)

        self.assertNotEqual(first_env, 99)


class ConcreteEnvironmentTest(unittest.TestCase):
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

        return links, symbolic_link_names

    def test_get_polish_notation_correct(self):
        for _ in range(0, 50):
            links, symbolic_link_names = ConcreteEnvironmentTest.get_random_links()

            env = ConcreteEnvironment(links)
            for link_name in symbolic_link_names:
                env.set_link(link_name, LinkState.UP)

            correct_pn = ""
            for link in sorted(links, key=lambda l: l.name):
                if link.state == LinkState.SYMBOLIC:
                    link.state = LinkState.UP
                link_pn = link.get_polish_notation()

                if not correct_pn:
                    correct_pn = "( {link} )".format(link=link_pn, )
                else:
                    correct_pn = "( AND {prev_links} ( {link} ) )".format(prev_links=correct_pn, link=link_pn, )

            test_pn = env.get_polish_notation()

            self.assertEqual(test_pn, correct_pn)

    def test_get_polish_notation_fail(self):
        for _ in range(0, 50):
            links, symbolic_link_names = ConcreteEnvironmentTest.get_random_links()

            if symbolic_link_names:
                env = ConcreteEnvironment(links)
                self.assertRaises(AssertionError, env.get_polish_notation)

    def test_get_links(self):
        for _ in range(0, 50):
            links, _ = ConcreteEnvironmentTest.get_random_links()

            state = random.choice([LinkState.UP, LinkState.DOWN, LinkState.SYMBOLIC])

            env = ConcreteEnvironment(links)
            test_links = env.get_links(state=state)

            correct_links = list()
            for link in links:
                if link.state == state:
                    correct_links.append(link)

            self.assertCountEqual(test_links, correct_links)

    def test_equality_equal(self):
        for _ in range(0, 50):
            links, _ = ConcreteEnvironmentTest.get_random_links()

            env1 = ConcreteEnvironment(links)
            env2 = ConcreteEnvironment(links)

            self.assertEqual(env1, env2)

    def test_equality_not_equal(self):
        for _ in range(0, 50):
            links1, _ = ConcreteEnvironmentTest.get_random_links()
            links2, _ = ConcreteEnvironmentTest.get_random_links()

            if sorted(links1, key=lambda l: l.id) != sorted(links2, key=lambda l: l.id):
                env1 = ConcreteEnvironment(links1)
                env2 = ConcreteEnvironment(links2)

                self.assertNotEqual(env1, env2)

    def test_from_failed_edges(self):
        for _ in range(0, 50):
            links, _ = ConcreteEnvironmentTest.get_random_links()

            k = random.randint(0, len(links))
            failed_link_names = [link.name for link in random.sample(links, k)]

            test_env = ConcreteEnvironment.from_failed_links(links, failed_link_names)

            correct_env = ConcreteEnvironment(links)
            for link_name in correct_env.links.keys():
                if link_name in failed_link_names:
                    correct_env.set_link(link_name, LinkState.DOWN)
                else:
                    correct_env.set_link(link_name, LinkState.UP)

            self.assertEqual(test_env, correct_env)


if __name__ == "__main__":
    unittest.main()
