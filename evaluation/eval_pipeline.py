#!/usr/bin/env python
# Author: Ruediger Birkner (Networked Systems Group at ETH Zurich)

import argparse
import datetime
import json
import os

from evaluation.utils.helper import init_dp_engine
from evaluation.utils.helper import init_backend
from evaluation.utils.helper import init_manager
from evaluation.utils.helper import build_network
from evaluation.utils.helper import get_sampler
from evaluation.utils.helper import get_policy_db

from evaluation.pipeline import Pipeline
from evaluation.utils.logger import get_logger

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
    sampling_modes = ["sum"]
    waypoints_min = 3  #
    waypoints_fraction = 5
    all_max_failures = [1, 2, 3]
    window_size = 10
    trimming = [True]

    # init stats file
    stats_file = "../logs/pipeline_%s_%s.log" % (scenario, '{:%Y%m%d-%H%M%S}'.format(datetime.datetime.now()),)
    with open(stats_file, "w") as outfile:
        outfile.write("# Scenario %s\n" % scenario)
        outfile.write("# Measurement of Sampling and Time to Verify Resulting Policy Guess\n\n")

    file_path = os.path.join(base_path, "run_scenario.json")
    with open(file_path, "r") as in_file:
        available_runs = json.load(in_file)

    num_runs = min(num_runs, len(available_runs))

    for trim in trimming:
        for run_id in range(0, num_runs):
            logger.info("Starting with run {run_id}".format(run_id=run_id))

            run_data = available_runs[run_id]

            # all the necessary paths where config, fib and topology files are being stored
            scenario_path = os.path.join(base_path, run_data["path"])
            config_path = os.path.join(scenario_path, "configs")
            fib_path = os.path.join(scenario_path, "fibs")

            # initialize the backend
            init_backend(ms_manager, scenario, batfish_path, config_path, batfish_port)

            for max_failures in all_max_failures:

                # initialize all the data structures
                network, netenv, waypoints = build_network(ms_manager.backend, scenario_path, max_failures,
                                                           waypoints_min, waypoints_fraction)

                with open(stats_file, "a") as outfile:
                    outfile.write("# Scenario %s - Run %d\n" % (scenario, run_id))
                    output = "# Nodes: {num_nodes}; ".format(num_nodes=len(network.nodes()))
                    output += "Edges: {num_edges}; ".format(num_edges=len(network.get_undirected_edges()))
                    output += "Waypoints: {wps}; ".format(wps=", ".join(waypoints))
                    output += "Trimming: {trim}; ".format(trim=trim)
                    output += "Failures: {k}\n\n".format(k=netenv.k_failures)
                    logger.info(output)
                    outfile.write(output)

                logger.info("RunID {run_id} - Scenario {scenario} {version} - Max Failures {failures}".format(
                            run_id=run_id, failures=max_failures, scenario=scenario, version=run_data["path"]))

                dp_engine = init_dp_engine(network, fib_path, debug=args.debug)

                for sampling_mode in sampling_modes:
                    logger.info("RunID {run_id} - Max Failures {failures} - Mode {sm}".format(
                        run_id=run_id, failures=max_failures, sm=sampling_mode))

                    # restart backend
                    ms_manager.restart(force=True)

                    # init policy Database
                    policy_db = get_policy_db(network, waypoints=waypoints, debug=debug)

                    # get sampler
                    sampler = get_sampler(sampling_mode, netenv, policy_db, seed)

                    # RUN PIPELINE
                    pipeline = Pipeline(policy_db, sampler, dp_engine, netenv, ms_manager, window_size, network, debug)
                    pipeline.run(trim_policies=trim)
                    pipeline.write_stats(stats_file, scenario, sampling_mode, run_id)

    # completely kill Minesweeper
    ms_manager.stop(0, force_stop=True)
    logger.info('Done with everything')
