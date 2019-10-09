#!/usr/bin/env python
# Author: Ruediger Birkner (Networked Systems Group at ETH Zurich)

from config2spec.netenv.sampler import Sampler


class EnumerateSampler(Sampler):
    def __init__(self, netenv, max_num_samples=None, seed=None, use_provided_samples=False, debug=False):
        super(EnumerateSampler, self).__init__(netenv, max_num_samples, seed, use_provided_samples, False, debug)

    def get_next_env(self):
        # first check if there are any samples left, if not, return None
        if not self.more_envs():
            self.logger.debug("No more states left for sampling")
            return None

        concrete_env = self.netenv.get_concrete_env(self.used_samples)
        if self.use_env(concrete_env):
            return concrete_env
        else:
            self.logger.debug("Couldn't find an unused environment and hence, stop here.")
            return None
