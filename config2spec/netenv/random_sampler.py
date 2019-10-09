#!/usr/bin/env python
# Author: Ruediger Birkner (Networked Systems Group at ETH Zurich)

from config2spec.netenv.sampler import Sampler


class RandomSampler(Sampler):
    def __init__(self, netenv, max_num_samples=None, seed=None, use_provided_samples=False, debug=False):
        super(RandomSampler, self).__init__(netenv, max_num_samples, seed, use_provided_samples, False, debug)

    def get_next_env(self, provided_env=None):
        # first check if there are any samples left, if not, return None
        if not self.more_envs():
            self.logger.debug("No more states left for sampling")
            return None

        # check if the provided sample has already been used, if not, use it and for that we need to find its sample_id
        if self.use_provided_samples and provided_env and provided_env not in self.used_concrete_envs:
            self.used_concrete_envs.add(provided_env)
            self.used_samples += 1
            return provided_env

        # get an actual sample
        else:
            tries = 0
            while True:
                tries += 1

                sample = self.sample_random.randint(0, self.total_samples - 1)
                concrete_env = self.netenv.get_concrete_env(sample)

                if self.use_env(concrete_env):
                    return concrete_env
                elif tries > 100:
                    self.logger.debug("Couldn't find an unused environment and hence, stop here.")
                    return None
