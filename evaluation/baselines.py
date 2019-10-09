#!/usr/bin/env python
# Author: Ruediger Birkner (Networked Systems Group at ETH Zurich)

import numpy as np
import time

from evaluation.utils.logger import get_logger

from config2spec.topology.links import LinkState
from config2spec.policies.policy_db import PolicyStatus


class SamplingStats(object):
    def __init__(self, stime, guess_size, failed):
        self.time = stime
        self.guess_size = guess_size
        self.failed = failed

    @staticmethod
    def get_heading():
        return "Guess Size, Time, Failed Sample,"

    def __str__(self):
        return "SA: {size}, {time}, {fail}".format(size=self.guess_size, time=self.time, fail=self.failed)


class VerificationStats(object):
    def __init__(self, vtime, query_size, num_verified, num_violated, num_unknown):
        self.time = vtime
        self.query_size = query_size
        self.num_verified = num_verified
        self.num_violated = num_violated
        self.num_unknown = num_unknown

    @staticmethod
    def get_heading():
        return "Query Size, Num Verified, Num Violated, Num Unknown, Time,"

    def __str__(self):
        return "VE: {size}, {nver}, {nvio}, {nunk}, {time}".format(size=self.query_size, nver=self.num_verified,
                                                                   nvio=self.num_violated, nunk=self.num_unknown,
                                                                   time=self.time)


class VerificationOnly(object):
    def __init__(self, policy_db, netenv, ms_manager, debug=False):
        self.logger = get_logger("Dense-Sparse-Pipeline", 'DEBUG' if debug else 'INFO')

        self.policy_db = policy_db
        self.netenv = netenv
        self.ms_manager = ms_manager

        # statistics
        self.stats = list()

    def verify(self):
        start_time = time.time()

        # pick next policy/policies to check
        query = self.policy_db.get_query(environment=self.netenv, group=True)

        # check policies with Minesweeper
        response = self.ms_manager.check_query(query)

        # update policy db
        if response.all_hold():
            verified_sources = response.holds()
            for source in verified_sources:
                self.policy_db.update_policy(response.type, response.subnet, response.specifics,
                                             PolicyStatus.HOLDS, source=source)
        else:
            failed_sources = response.holds_not()
            for source in failed_sources:
                self.policy_db.update_policy(response.type, response.subnet, response.specifics,
                                             PolicyStatus.HOLDSNOT, source=source)

        # update stats
        verification_time = time.time() - start_time
        size = len(query.sources)
        verified = len(response.holds())
        violated = len(response.holds_not())
        unknown = size - verified - violated

        self.stats.append(VerificationStats(verification_time, size, verified, violated, unknown))

        return True

    def run(self, trim_policies=False):
        self.logger.info("Starting the Verification Only Baseline.")
        num_steps = 0
        while True:
            remaining_policies = self.policy_db.num_policies(status=PolicyStatus.UNKNOWN)

            # logging
            if num_steps % 100 == 0:
                self.logger.info("Step {}: There are {} policies remaining.".format(num_steps, remaining_policies))
            num_steps += 1

            # check if we are done
            if remaining_policies == 0:
                break

            success = self.verify()

            # check if something failed
            if not success:
                self.logger.info("Something failed (most likely the dataplane sampling)")
                break

        return

    def write_stats(self, stats_file, scenario, sampling_mode, run_id, policy_time):
        with open(stats_file, "a") as outfile:
            # general info about the run
            outfile.write("# {scenario} - {run_id} - {sampling_mode}\n".format(
                scenario=scenario, run_id=run_id, sampling_mode=sampling_mode))

            outfile.write("# Verification Stats structure: {}\n".format(VerificationStats.get_heading()))

            outfile.write("PG: {}\n".format(policy_time))

            # stats in order
            for j, tmp_stats in enumerate(self.stats):
                outfile.write("{}\n".format(str(tmp_stats)))

            # write final stats to file
            num_pols = self.policy_db.num_policies()
            num_holds = self.policy_db.num_policies(status=PolicyStatus.HOLDS)
            num_holdsnot = self.policy_db.num_policies(status=PolicyStatus.HOLDSNOT)
            num_unknown = self.policy_db.num_policies(status=PolicyStatus.UNKNOWN)
            outfile.write("# Total Policies: {num_pols} - HOLDS: {num_holds} - HOLDS NOT: {num_holdsnot}"
                          " - UNKNOWN: {num_unknown}\n\n".format(num_pols=num_pols, num_holds=num_holds,
                                                                 num_holdsnot=num_holdsnot,
                                                                 num_unknown=num_unknown))


class SamplingOnly(object):
    def __init__(self, policy_db, sampler, dp_engine, netenv, ms_manager, network, debug=False):
        self.logger = get_logger("Dense-Sparse-Pipeline", 'DEBUG' if debug else 'INFO')

        self.policy_db = policy_db
        self.sampler = sampler
        self.dp_engine = dp_engine
        self.netenv = netenv
        self.ms_manager = ms_manager
        self.network = network

        self.first = True
        self.prev_forwarding_graphs = None

        # statistics
        self.stats = list()

    def sample(self):
        start_time = time.time()

        # pick the concrete env to use
        if self.first:
            self.first = False
            concrete_env = self.sampler.get_all_up()
        elif self.sampler.fwd_state_based:
            concrete_env = self.sampler.get_next_env(self.prev_forwarding_graphs)
        else:
            concrete_env = self.sampler.get_next_env()

        # compute the dataplane and check the policies that hold
        failure = True
        guess_size = -1

        if concrete_env:
            failed_edges = concrete_env.get_links(state=LinkState.DOWN)
            fib_file_name = self.ms_manager.get_dataplane(failed_edges)
            if fib_file_name:
                forwarding_graphs = self.dp_engine.get_forwarding_graphs(fib_file_name)
                dominator_graphs = self.dp_engine.get_dominator_graphs()
                _, guess_size = self.policy_db.update_policies(9, forwarding_graphs, dominator_graphs)
                failure = False

                self.prev_forwarding_graphs = forwarding_graphs

            sampling_time = time.time() - start_time
            self.stats.append(SamplingStats(sampling_time, guess_size, failure))

            return True
        else:
            self.logger.error("Couldn't find another unused sample!")
            return False

    def run(self):
        self.logger.info("Start running the pipeline by computing the first sample.")

        num_steps = 0
        while True:
            remaining_samples = self.sampler.remaining_samples()

            # logging
            if num_steps % 100 == 0:
                self.logger.info("Step {}: There are {} samples remaining.".format(num_steps, remaining_samples))
            num_steps += 1

            # check if we are done
            if remaining_samples == 0:
                break

            success = self.sample()

            # check if something failed
            if not success:
                self.logger.info("Something failed (most likely the dataplane sampling)")
                break

        # as we are done, we need to change all the unknown policies to ones that hold
        self.policy_db.change_status(PolicyStatus.UNKNOWN, PolicyStatus.HOLDS)

        return

    def write_stats(self, stats_file, scenario, baseline, run_id):
        with open(stats_file, "a") as outfile:
            # general info about the run
            outfile.write("# {scenario} - {run_id} - {baseline}\n".format(
                scenario=scenario, run_id=run_id, baseline=baseline))

            outfile.write("# Sampling Stats Structure: {}\n".format(SamplingStats.get_heading()))

            # stats in order
            for j, tmp_stats in enumerate(self.stats):
                outfile.write("{}\n".format(str(tmp_stats)))

            # write final stats to file
            num_pols = self.policy_db.num_policies()
            num_holds = self.policy_db.num_policies(status=PolicyStatus.HOLDS)
            num_holdsnot = self.policy_db.num_policies(status=PolicyStatus.HOLDSNOT)
            num_unknown = self.policy_db.num_policies(status=PolicyStatus.UNKNOWN)
            outfile.write("# Total Policies: {num_pols} - HOLDS: {num_holds} - HOLDS NOT: {num_holdsnot}"
                          " - UNKNOWN: {num_unknown}\n\n".format(num_pols=num_pols, num_holds=num_holds,
                                                                 num_holdsnot=num_holdsnot,
                                                                 num_unknown=num_unknown))