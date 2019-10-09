#!/usr/bin/env python
# Author: Ruediger Birkner (Networked Systems Group at ETH Zurich)

import argparse
import datetime
import os
import json

from evaluation.utils.helper import init_dp_engine
from evaluation.utils.helper import init_backend
from evaluation.utils.helper import init_manager
from evaluation.utils.helper import build_network
from evaluation.utils.helper import get_sampler
from evaluation.utils.logger import get_logger
from evaluation.policy_verification import verify_all_policies
from evaluation.run_sampling import run_sampling


from config2spec.policies.policy_db import PolicyDB
from config2spec.policies.policy_db import PolicyStatus


''' main '''
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('path', help='path to scenario')
    parser.add_argument('backend_path', help='path to backend executable', type=str)
    parser.add_argument('batfish_path', help='path to cloned Batfish GitHub repo', type=str)
    parser.add_argument('-p', '--port', help='port batfish is listening on', type=int, default=8192)
    parser.add_argument('-d', '--debug', help='enable debug output', action='store_true')
    parser.add_argument('-bd', '--backend_debug', help='enable debug output for the backend', action='store_true')
    args = parser.parse_args()

    # init logger
    debug = args.debug
    logger = get_logger("Sampling Strategy Evaluation", 'DEBUG' if debug else 'INFO')

    # name of the scenario
    scenario = os.path.basename(args.path)

    # all the necessary paths where config, fib and topology files are being stored
    batfish_path = args.batfish_path  # path to cloned Batfish repo directory
    backend_path = args.backend_path  # path to Batfish executable
    base_path = args.path

    batfish_port = args.port

    # create backend manager
    ms_manager = init_manager(backend_path, batfish_port)

    # general settings
    seed = 4704  # seed for the random number generator
    num_runs = 5  # number of different configs we should try for this scenario
    samples_per_run = [500]  # number of samples to try
    sampling_modes = ["random", "sum"]
    waypoints_min = 3  #
    waypoints_fraction = 5
    default_max_failures = 3

    # init stats file
    log_file = "../logs/sampling_%s_%s.log" % (scenario, '{:%Y%m%d-%H%M%S}'.format(datetime.datetime.now()),)
    with open(log_file, "w") as outfile:
        outfile.write("# Scenario %s\n" % scenario)
        outfile.write("# Measurement of Sampling and Time to Verify Resulting Policy Guess\n\n")

    # read all available runs
    file_path = os.path.join(base_path, "run_scenario.json")
    with open(file_path, "r") as in_file:
        available_runs = json.load(in_file)

    num_runs = min(num_runs, len(available_runs))

    for run_id in range(0, num_runs):
        logger.info("Starting with run {run_id}".format(run_id=run_id))

        run_data = available_runs[run_id]

        # all the necessary paths where config, fib and topology files are being stored
        scenario_path = os.path.join(base_path, run_data["path"])
        config_path = os.path.join(scenario_path, 'configs')
        fib_path = os.path.join(scenario_path, 'fibs')

        # initialize the backend
        init_backend(ms_manager, scenario, batfish_path, config_path, batfish_port)

        max_failures = default_max_failures

        # initialize all the data structures
        network, netenv, waypoints = build_network(
            ms_manager.backend, scenario_path, max_failures, waypoints_min, waypoints_fraction)

        with open(log_file, "a") as outfile:
            outfile.write("# Scenario %s - Run %d\n" % (scenario, run_id))
            output = "# Nodes: {num_nodes}; ".format(num_nodes=len(network.nodes()))
            output += "Edges: {num_edges}; ".format(num_edges=len(network.get_undirected_edges()))
            output += "Waypoints: {wps}; ".format(wps=", ".join(waypoints))
            output += "Failures: {k}\n\n".format(k=netenv.k_failures)
            logger.info(output)
            outfile.write(output)

        for num_samples in samples_per_run:
            logger.info(
                "RunID {run_id} - Scenario {scenario} {version} - Num Samples {num_samples}".format(
                    run_id=run_id, num_samples=num_samples, scenario=scenario, version=run_data["path"]))

            dp_engine = init_dp_engine(network, fib_path, debug=args.debug)

            # run it once for both sampling methods
            for i, sampling_mode in enumerate(sampling_modes):
                logger.info("RunID {run_id} - Num Samples {num_samples} - Mode {sm} - Sample {sid}".format(
                    run_id=run_id, num_samples=num_samples, sm=sampling_mode, sid=i))

                # init policy Database
                policy_db = PolicyDB(network, waypoints=waypoints, debug=debug)

                # get sampler
                sampler = get_sampler(sampling_mode, netenv, policy_db, seed)

                # do the sampling
                sampling_stats = run_sampling(num_samples, sampler, policy_db, ms_manager, dp_engine)

                # write stats to file
                with open(log_file, "a") as outfile:
                    outfile.write("# {scenario} - {run_id} - {sampling_mode} - {num_samples} - Sampling\n".format(
                        scenario=scenario, run_id=run_id, sampling_mode=sampling_mode, num_samples=num_samples
                    ))

                    for j, tmp_stats in enumerate(sampling_stats):
                        if j == 0:
                            outfile.write("{}\n".format(tmp_stats.get_heading()))
                        outfile.write("{}\n".format(str(tmp_stats)))

                # once per run, verify all the policies such that we know how much holds
                if i == len(sampling_modes) - 1:
                    logger.info("RunID {run_id} - Num Samples {num_samples} - Mode {sm} - Sample {sid} - "
                                "Verification".format(run_id=run_id, num_samples=num_samples, sm=sampling_mode, sid=i))

                    # trim as much as you can
                    connected_pairs = network.get_k_connected_routers(netenv.k_failures + 1)
                    num_trimmed = policy_db.trim_policies(connected_pairs)

                    verification_stats = verify_all_policies(policy_db, netenv, ms_manager, logger)

                    # write stats to file
                    with open(log_file, "a") as outfile:
                        outfile.write("# {scenario} - {run_id} - {sampling_mode} - {num_samples} - "
                                      "Verification\n".format(scenario=scenario, run_id=run_id,
                                                              sampling_mode=sampling_mode, num_samples=num_samples)
                                      )

                        num_pols = policy_db.num_policies()
                        num_holds = policy_db.num_policies(status=PolicyStatus.HOLDS)
                        num_holdsnot = policy_db.num_policies(status=PolicyStatus.HOLDSNOT)
                        num_unknown = policy_db.num_policies(status=PolicyStatus.UNKNOWN)
                        outfile.write("# Total Policies: {num_pols} - HOLDS: {num_holds} - HOLDS NOT: {num_holdsnot}"
                                      " - UNKNOWN: {num_unknown} - Trimmed: {trimmed}\n".format(num_pols=num_pols,
                                                                                                num_holds=num_holds,
                                                                                                num_holdsnot=num_holdsnot,
                                                                                                num_unknown=num_unknown,
                                                                                                trimmed=num_trimmed)
                                      )

                        for j, tmp_stats in enumerate(verification_stats):
                            if j == 0:
                                outfile.write("{}\n".format(tmp_stats.get_heading()))
                            outfile.write("{}\n".format(str(tmp_stats)))

    # completely kill Minesweeper
    ms_manager.stop(0, force_stop=True)
    logger.info('Done with everything')
