#!/usr/bin/env python
# Author: Ruediger Birkner (Networked Systems Group at ETH Zurich)

import argparse
import os

from helper import build_network
from helper import get_logger
from helper import get_policy_db
from helper import get_sampler
from helper import init_backend
from helper import init_dp_engine
from helper import init_manager
from helper import Pipeline
from config2spec.policies.policy_db import PolicyStatus

''' main '''
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('scenario_path', help='path to scenario', type=str)
    parser.add_argument('backend_path', help='path to backend executable', type=str)
    parser.add_argument('batfish_path', help='path to cloned Batfish GitHub repo', type=str)
    parser.add_argument('-p', '--port', help='port batfish is listening on', type=int, default=8192)
    parser.add_argument('-d', '--debug', help='enable debug output', action='store_true')
    parser.add_argument('-bd', '--backend_debug', help='enable debug output for the backend', action='store_true')
    parser.add_argument('-mf', '--max_failures', help='maximum amount of failures to allow', type=int)
    args = parser.parse_args()

    # init logger
    debug = args.debug
    logger = get_logger("Config2Spec", 'DEBUG' if debug else 'INFO')

    # name of the scenario
    scenario = os.path.basename(args.scenario_path)

    # all the necessary paths where config, fib and topology files are being stored
    batfish_path = args.batfish_path  # path to cloned Batfish repo directory
    backend_path = args.backend_path  # path to Batfish executable
    scenario_path = args.scenario_path

    batfish_port = args.port

    # create backend manager
    ms_manager = init_manager(backend_path, batfish_port)

    # general settings
    seed = 8006
    window_size = 10
    sampling_mode = "sum"
    trimming = True
    waypoints_min = 3
    waypoints_fraction = 5

    # maximum amount of failures to be allowed
    if args.max_failures is None:
        max_failures = 1
    else:
        max_failures = args.max_failures

    # all the necessary paths where config, fib and topology files are being stored
    config_path = os.path.join(scenario_path, "configs")
    fib_path = os.path.join(scenario_path, "fibs")

    # initialize the backend
    init_backend(ms_manager, scenario, batfish_path, config_path, batfish_port)

    # initialize all the data structures
    network, netenv, waypoints = build_network(ms_manager.backend, scenario_path, max_failures,
                                               waypoints_min, waypoints_fraction)
    dp_engine = init_dp_engine(network, fib_path, debug=args.debug)

    # init policy Database
    policy_db = get_policy_db(network, waypoints=waypoints, debug=debug)

    # get sampler
    sampler = get_sampler(sampling_mode, netenv, policy_db, seed)

    # run Config2Spec pipeline
    pipeline = Pipeline(policy_db, sampler, dp_engine, netenv, ms_manager, window_size, network, debug)
    pipeline.run(trim_policies=trimming)

    # completely kill Minesweeper
    ms_manager.stop(0, force_stop=True)

    # store the specification
    dump_file = "policies.csv"
    dump_path = os.path.join(scenario_path, dump_file)
    policy_db.dump(dump_path)

    spec_size = policy_db.num_policies(status=PolicyStatus.HOLDS)
    logger.info('Done with everything - The specification consists of {} policies.'.format(spec_size))
