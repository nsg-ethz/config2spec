#!/usr/bin/env python
# Author: Ruediger Birkner (Networked Systems Group at ETH Zurich)

import random

from config2spec.utils.logger import get_logger


class Sampler(object):
    def __init__(self, netenv, max_num_samples=None, seed=None, use_provided_samples=False, fwd_state_based=False, debug=False):
        self.debug = debug
        self.logger = get_logger('Sampler', 'DEBUG' if debug else 'INFO')

        self.fwd_state_based = fwd_state_based

        self.sample_random = random.Random(seed)

        self.netenv = netenv
        self.total_samples = netenv.num_concrete_envs

        self.use_provided_samples = use_provided_samples

        self.used_samples = 0
        self.used_concrete_envs = set()

        self.next_sample_in_order = 0

        if max_num_samples is not None:
            self.max_num_samples = min(max_num_samples, self.total_samples)
        else:
            self.max_num_samples = self.total_samples

    def more_envs(self):
        return self.used_samples < self.max_num_samples

    def use_env(self, concrete_env):
        if concrete_env not in self.used_concrete_envs:
            self.used_concrete_envs.add(concrete_env)
            self.used_samples += 1
            return True
        else:
            return False

    def get_all_up(self):
        concrete_env = self.netenv.get_concrete_env(0)
        self.use_env(concrete_env)
        return concrete_env

    def remaining_samples(self):
        return self.total_samples - self.used_samples

    def get_next_unused_env(self):
        if self.more_envs():
            next_concrete_env = self.netenv.get_concrete_env(self.next_sample_in_order)

            while not self.use_env(next_concrete_env):
                self.next_sample_in_order += 1
                next_concrete_env = self.netenv.get_concrete_env(self.next_sample_in_order)

            self.next_sample_in_order += 1

            return next_concrete_env
        else:
            self.logger.debug("Couldn't find an unused environment and hence, stop here.")
            return None