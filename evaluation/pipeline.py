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


class TrimmingStats(object):
    def __init__(self, ttime, num_trimmed, num_verified, num_violated, num_unknown):
        self.time = ttime
        self.num_trimmed = num_trimmed
        self.num_verified = num_verified
        self.num_violated = num_violated
        self.num_unknown = num_unknown

    @staticmethod
    def get_heading():
        return "Num Trimmed, Num Verified, Num Violated, Num Unknown, Time,"

    def __str__(self):
        return "TR: {size}, {nver}, {nvio}, {nunk}, {time}".format(size=self.num_trimmed, nver=self.num_verified,
                                                                   nvio=self.num_violated, nunk=self.num_unknown,
                                                                   time=self.time)


class SwitchStats(object):
    def __init__(self, from_mode, to_mode, action, remaining_policies, remaining_samples):
        self.from_mode = from_mode
        self.to_mode = to_mode
        self.action = action
        self.remaining_policies = remaining_policies
        self.remaining_samples = remaining_samples

    def __str__(self):
        return "# SWITCH: {} -> {} - {} - Num Policies: {}; Num Samples: {}".format(self.from_mode, self.to_mode,
                                                                                    self.action,
                                                                                    self.remaining_policies,
                                                                                    self.remaining_samples)


class Settings(object):
    def __init__(self):
        self.seed = 8006  # seed for the random number generator
        self.sampling_mode = "randomset"
        self.waypoints = []  #
        self.max_failures = 3  # maximum number of links to fail at a time

    def __str__(self):
        output = "Seed: {}; ".format(self.seed)
        output += "Sampling Mode: {}; ".format(self.sampling_mode)
        output += "Waypoints: {}; ".format(", ".join(self.waypoints))
        output += "Max Failures: {}; ".format(self.max_failures)
        return output


class SlidingTimer(object):
    def __init__(self, window_size):
        self.window_size = window_size

        self.times = list()
        self.eliminated_policies = list()

        self.infinity = 10000000

    def mean_time_per_item(self):
        if self.times:
            # if the list of times is shorter than the window size this still works
            mean_time = np.mean(self.times[-self.window_size:])
            return mean_time
        else:
            return 0

    def mean_time_per_policy(self):
        if self.times:
            total_time = sum(self.times[-self.window_size:])
            num_policies = sum(self.eliminated_policies[-self.window_size:])

            if num_policies > 0:
                return total_time/num_policies
            return self.infinity
        else:
            return 0

    def estimate_remaining_time(self, num_samples):
        mean_time = self.mean_time_per_item()

        if mean_time:
            return num_samples * mean_time
        else:
            return 0

    def update(self, time, num_eliminated_policies):
        self.times.append(time)
        self.eliminated_policies.append(num_eliminated_policies)

    def full_window(self):
        return len(self.times) == self.window_size


class Pipeline(object):
    def __init__(self, policy_db, sampler, dp_engine, netenv, ms_manager, window_size, network, debug=False):
        self.logger = get_logger("Dense-Sparse-Pipeline", 'DEBUG' if debug else 'INFO')

        self.policy_db = policy_db
        self.sampler = sampler
        self.dp_engine = dp_engine
        self.netenv = netenv
        self.ms_manager = ms_manager
        self.network = network

        # set up time analysis
        self.sampling_times = SlidingTimer(window_size)
        self.verification_times = SlidingTimer(window_size)

        # temporary variables
        self.prev_forwarding_graphs = None
        self.prev_guess_size = -1

        # statistics
        self.stats = list()

    def sample(self, first=False):
        start_time = time.time()

        # pick the concrete env to use
        if first:
            concrete_env = self.sampler.get_all_up()
        elif self.sampler.fwd_state_based:
            concrete_env = self.sampler.get_next_env(self.prev_forwarding_graphs)
        else:
            concrete_env = self.sampler.get_next_env()

        # compute the dataplane and check the policies that hold
        failure = True
        num_eliminated_policies = -1
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
                if self.prev_guess_size >= 0:
                    num_eliminated_policies = self.prev_guess_size - guess_size
                self.prev_guess_size = guess_size

            sampling_time = time.time() - start_time
            if num_eliminated_policies >= 0:
                self.sampling_times.update(sampling_time, num_eliminated_policies)

            self.stats.append(SamplingStats(sampling_time, guess_size, failure))

            return True
        else:
            self.logger.error("Couldn't find another unused sample!")
            return False

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

        self.verification_times.update(verification_time, verified + violated)
        self.stats.append(VerificationStats(verification_time, size, verified, violated, unknown))

        return True

    def trim(self):
        start_time = time.time()
        connected_pairs = self.network.get_k_connected_routers(self.netenv.k_failures + 1)
        num_trimmed = self.policy_db.trim_policies(connected_pairs)

        # update stats
        trim_time = time.time() - start_time
        num_verified = self.policy_db.num_policies(status=PolicyStatus.HOLDS)
        num_violated = self.policy_db.num_policies(status=PolicyStatus.HOLDSNOT)
        num_unknown = self.policy_db.num_policies(status=PolicyStatus.UNKNOWN)

        self.stats.append(TrimmingStats(trim_time, num_trimmed, num_verified, num_violated, num_unknown))

    def run(self, trim_policies=False):
        self.logger.info("Start running the pipeline by computing the first sample.")

        # start actual policy learning with a first sample - all links up
        success = self.sample(first=True)
        if not success:
            self.logger.info("Dataplane sampling failed...")
            return

        self.logger.info("Running a couple of queries to init the verification timer.")
        # run enough queries to Minesweeper to match the window size of the timers
        while not self.verification_times.full_window():
            success = self.verify()

        self.logger.info("Starting the actual loop.")
        # start with elimination of dense violations using sampling, then decide whether to continue sampling or switch
        # to verification depending on the expected run time.
        remaining_samples = self.sampler.remaining_samples()
        remaining_policies = self.policy_db.num_policies(status=PolicyStatus.UNKNOWN)
        self.stats.append(SwitchStats("init", "dense", "sampling", remaining_policies, remaining_samples))
        dense = True
        sparse_sampling = True
        num_steps = 0
        while True:
            remaining_samples = self.sampler.remaining_samples()
            remaining_policies = self.policy_db.num_policies(status=PolicyStatus.UNKNOWN)

            # logging
            if num_steps % 100 == 0:
                self.logger.info("Step {}: There are {} samples and {} policies remaining.".format(num_steps, remaining_samples, remaining_policies))
            num_steps += 1

            # check if we are done
            if remaining_samples == 0 or remaining_policies == 0:
                break

            # dense elimination - in the beginning we are in the dense elimination phase in which we try to quickly
            # narrow done the policy guess by using a few dataplane samples.
            sampling_time = self.sampling_times.mean_time_per_policy()
            verification_time = self.verification_times.mean_time_per_policy()
            if sampling_time <= verification_time:

                if not dense:
                    self.logger.info("Switching back to dense elimination.")
                    self.stats.append(SwitchStats("sparse", "dense", "sampling", remaining_policies, remaining_samples))
                    dense = True

                success = self.sample()

            # sparse elimination - once the time needed to eliminate a policy by sampling is the same or less than
            # by verification, we switch to sparse elimination. In this mode, we decide based on an estimate of the
            # remaining time whether we want to continue sampling or start verifying.
            else:
                if dense:
                    self.logger.info("Switching to sparse elimination.")
                    self.stats.append(SwitchStats("dense", "sparse", "sampling", remaining_policies, remaining_samples))
                    dense = False

                total_sampling_time = self.sampling_times.estimate_remaining_time(remaining_samples)
                total_verification_time = self.verification_times.estimate_remaining_time(remaining_policies)

                # stick with sampling
                if total_sampling_time <= total_verification_time:
                    if not sparse_sampling:
                        self.logger.info("Sparse: Switching to Sampling")
                        self.stats.append(SwitchStats("dense", "sparse", "sampling", remaining_policies, remaining_samples))
                        sparse_sampling = True
                    success = self.sample()

                # switch to verification
                else:
                    if sparse_sampling:
                        self.logger.info("Sparse: Switching to Verification")
                        self.stats.append(SwitchStats("dense", "sparse", "verification", remaining_policies, remaining_samples))
                        sparse_sampling = False

                    # if desired remove all policies from the guess that are physically not feasible due to the topology
                    if trim_policies:
                        self.logger.info("Trimming the policies.")
                        trim_policies = False
                        self.trim()
                    else:
                        success = self.verify()

            # check if something failed
            if not success:
                self.logger.info("Something failed (most likely the dataplane sampling)")
                break

        # as we are done, we need to change all the unknown policies to ones that hold
        self.policy_db.change_status(PolicyStatus.UNKNOWN, PolicyStatus.HOLDS)

        return

    def write_stats(self, stats_file, scenario, sampling_mode, run_id):
        with open(stats_file, "a") as outfile:
            # general info about the run
            outfile.write("# {scenario} - {run_id} - {sampling_mode}\n".format(
                scenario=scenario, run_id=run_id, sampling_mode=sampling_mode))

            outfile.write("# Sampling Stats Structure: {}\n".format(SamplingStats.get_heading()))
            outfile.write("# Verification Stats structure: {}\n".format(VerificationStats.get_heading()))

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