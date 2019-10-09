#!/usr/bin/env python
# Author: Ruediger Birkner (Networked Systems Group at ETH Zurich)

import random

from evaluation.utils.ms_manager import MinesweeperManager

from config2spec.backend.minesweeper import MinesweeperBackend
from config2spec.dataplane.batfish_engine import BatfishEngine
from config2spec.netenv.network_environment import NetworkEnvironment
from config2spec.netenv.enumerate_sampler import EnumerateSampler
from config2spec.netenv.link_set_sampler import BlockLinksPolicySetSampler
from config2spec.netenv.merge_set_sampler import MergePolicySetSampler
from config2spec.netenv.random_set_sampler import RandomPolicySetSampler
from config2spec.netenv.random_sampler import RandomSampler
from config2spec.netenv.set_sampler import PolicySetSampler
from config2spec.netenv.sum_sampler import PolicySumSampler
from config2spec.policies.policy_db import PolicyDB
from config2spec.topology.builder.minesweeper_builder import BackendTopologyBuilder
from config2spec.topology.links import Link
from config2spec.topology.links import LinkState


def init_manager(backend_path, port):
    ms_cmd = ['java', '-cp', '%s' % backend_path, 'org.batfish.backend.Backend', '%d' % port]
    print(ms_cmd)

    # creating minesweeper manager
    ms_manager = MinesweeperManager(ms_cmd, port)
    ms_manager.start()

    return ms_manager


def init_backend(ms_manager, scenario, base_path, config_path, port):
    # init the backend (Batfish/Minesweeper)
    ms_backend = MinesweeperBackend(base_path, scenario, config_path, url="http://localhost", port=port, debug=False)
    ms_backend.init_minesweeper()

    ms_manager.backend = ms_backend

    ms_manager.restart(backend_calls=0, force=True)


def build_network(backend, scenario_path, max_failures, waypoints_min, waypoints_fraction):
    topology_files = backend.get_topology()
    network = BackendTopologyBuilder.build_topology(topology_files, scenario_path)

    # get waypoints
    all_routers = network.nodes()
    num_waypoints = max(waypoints_min, int(len(all_routers) / waypoints_fraction))
    waypoints = random.sample(all_routers, num_waypoints)

    links = list()
    all_edges = network.get_undirected_edges()
    for i, edge in enumerate(all_edges):
        links.append(Link("l{id}".format(id=i), edge, LinkState.SYMBOLIC))

    # create the network environment
    netenv = NetworkEnvironment(links, k_failures=max_failures)

    return network, netenv, waypoints


def init_dp_engine(network, fib_path, debug=False):
    nodes = list(network.nodes())
    next_hops = network.next_hops
    simple_acls = network.simple_acls
    dp_engine = BatfishEngine(nodes, next_hops, simple_acls, fib_path, debug=debug)

    return dp_engine


def get_sampler(sampling_mode, netenv, policy_db, seed):
    if sampling_mode == "random":
        sampler = RandomSampler(netenv, seed=seed,
                                use_provided_samples=False, debug=False)
    elif sampling_mode == "sum":
        sampler = PolicySumSampler(netenv, policy_db, seed=seed,
                                   use_provided_samples=False, debug=False)
    elif sampling_mode == "enumerate":
        sampler = EnumerateSampler(netenv, seed=seed,
                                   use_provided_samples=False, debug=False)
    elif sampling_mode == "merge":
        sampler = MergePolicySetSampler(netenv, policy_db, seed=seed,
                                        use_provided_samples=False, debug=False)
    elif sampling_mode == "block":
        sampler = BlockLinksPolicySetSampler(netenv, policy_db, seed=seed,
                                             use_provided_samples=False, debug=False)
    elif sampling_mode == "randomset":
        sampler = RandomPolicySetSampler(netenv, policy_db, seed=seed,
                                         use_provided_samples=False, debug=False)
    else:
        sampler = PolicySetSampler(netenv, policy_db, seed=seed,
                                   use_provided_samples=False, debug=False)
    return sampler


def get_policy_db(network, waypoints=None, debug=False):
    return PolicyDB(network, waypoints=waypoints, debug=debug)
