#!/usr/bin/env python
# Author: Ruediger Birkner (Networked Systems Group at ETH Zurich)

from collections import Counter
from collections import defaultdict
from enum import Enum
import pandas as pd

from config2spec.backend.query import Query

from config2spec.policies.policy import Policy
from config2spec.policies.policy import PolicyType
from config2spec.policies.policy_guesser import PolicyGuesser

from config2spec.utils.logger import get_logger


class PolicyStatus(Enum):
    UNKNOWN = "unknown"
    HOLDS = "holds"
    HOLDSNOT = "holdsnot"


class PolicyDB(object):
    def __init__(self, network, waypoints=None, debug=False):
        # initialize logging
        self.debug = debug
        self.logger = get_logger("PolicyDB", "DEBUG" if debug else "INFO")

        self.init = False

        self.policy_guesser = PolicyGuesser(network, waypoints=waypoints, debug=debug)
        self.keys = ["type", "subnet", "specifics", "source"]

        self.policies = None  # dataframe with the columns - type, src, dst, specifics, policy status, environments
        self.previous_size = -1  # stores the size of the current policy guess

        self.tmp_state = None

    def update_policies(self, sample, forwarding_graphs, dominator_graphs, node_local_reachability=False):
        # get the policy guess
        policies = self.policy_guesser.get_policies(forwarding_graphs, dominator_graphs, node_local_reachability=node_local_reachability)
        change, previous_size = self.update_policies2(policies, sample)
        return change, previous_size

    def update_policies2(self, policies, sample):
        # create a dataframe from the policy guess
        # for this, we first need to make sure that we have unique keys in the dataframe
        unique_policies = defaultdict(set)
        for ptype, destination, specifics, source in policies:
            index = (ptype, destination.subnet, specifics, source)
            unique_policies[index].add(destination)

        unique_index = list(unique_policies.keys())
        policy_index = pd.MultiIndex.from_tuples(unique_index, names=self.keys)

        envs = [{sample}] * len(unique_policies)
        destinations = list(unique_policies.values())

        new_df = pd.DataFrame({
            "Status": pd.Series(PolicyStatus.UNKNOWN, index=policy_index),
            "Environments": pd.Series(envs, index=policy_index),
            "Destinations": pd.Series(destinations, index=policy_index),
        })

        # if this is the first policy guess, init the db
        if not self.init:
            self.init = True
            self.policies = new_df
            change = 1.0
            self.previous_size = len(self.policies)
        # else merge the new guess with the old ones. The old one is considered to be the left and the new one the right
        # in the merge
        else:
            # all policies that overlap (exist in both)
            overlapping_indexes = policy_index.intersection(self.policies.index)
            for env in self.policies.loc[overlapping_indexes, "Environments"]:
                env.add(sample)

            destination_series = pd.Series([dests1.union(dests2) for dests1, dests2 in
                                            zip(self.policies.loc[overlapping_indexes, "Destinations"],
                                                new_df.loc[overlapping_indexes, "Destinations"])],
                                           index=overlapping_indexes)
            self.policies.loc[overlapping_indexes, "Destinations"] = destination_series

            # all policies which are already in the db, but don't hold for the given sample
            left_only_indexes = self.policies.index.difference(policy_index)
            self.policies.loc[left_only_indexes, "Status"] = PolicyStatus.HOLDSNOT

            # all policies which are not yet in the db, but hold for the given sample
            right_only_indexes = policy_index.difference(self.policies.index)
            envs = [{sample}] * len(right_only_indexes)
            policies = pd.DataFrame({
                "Status": pd.Series(PolicyStatus.HOLDSNOT, index=right_only_indexes),
                "Environments": pd.Series(envs, index=right_only_indexes),
                "Destinations": new_df.loc[right_only_indexes, "Destinations"]
            })
            self.policies = self.policies.append(policies)

            # computing the size of the policy guess
            current_size = len(self.policies[(self.policies["Status"] == PolicyStatus.HOLDS) |
                                             (self.policies["Status"] == PolicyStatus.UNKNOWN)])

            if self.previous_size == 0:
                change = 0.0
            else:
                change = float(self.previous_size - current_size)/float(self.previous_size)

            self.previous_size = current_size

        self.policies["Sources"] = self.policies.index.get_level_values("source")
        self.policies.sort_index()

        return change, self.previous_size

    def use_response(self, response):
        if response.holds_all():
            self.update_policy(response.type, response.destination, response.specifics, PolicyStatus.HOLDS)
        else:
            for failed_source in response.failed_sources():
                self.update_policy(response.type, response.destination, response.specifics, PolicyStatus.HOLDSNOT, source=failed_source)

    def update_policy(self, policy_type, destination, specifics, status, source=None):
        if source:
            self.policies.at[(policy_type, destination, specifics, source), "Status"] = status
        else:
            self.policies.loc[(policy_type, destination, specifics), "Status"] = status

    def change_status(self, current_status, next_status):
        self.policies.loc[self.policies["Status"] == current_status, "Status"] = next_status

    def num_policies(self, status=None):
        if not self.init:
            return 0
        if status:
            num_policies = len(self.policies[self.policies["Status"] == status])
        else:
            num_policies = len(self.policies)
        return num_policies

    def get_raw_policy(self, status=None, group=False):
        if not self.init:
            return None
        if status:
            raw_policies = self.policies[self.policies["Status"] == status]
        else:
            raw_policies = self.policies.iloc[0].name

        if group:
            raw_group = raw_policies.groupby(["type", "subnet", "specifics"], sort=False).aggregate({"Sources": list, "Destinations": list}).iloc[0]

            policy_type, _, specifics = raw_group.name
            destination = set.union(*raw_group["Destinations"])
            sources = raw_group["Sources"]

            raw_policy = (policy_type, sources, destination, specifics)
        else:
            tmp_policy = raw_policies.iloc[0].name
            destination = set.union(*raw_policies.iloc[0, "Destinations"])
            raw_policy = (tmp_policy[0], [tmp_policy[3]], destination, tmp_policy[2])

        return raw_policy

    def get_policy(self, status=None, group=False):
        raw_policy = self.get_raw_policy(status=status, group=group)
        policy = Policy.get_policy(raw_policy[0], raw_policy[1], [raw_policy[2]], raw_policy[3])
        return policy

    def get_all_policies(self, status=None):
        if not self.init:
            return list()
        if status:
            policies = self.policies[self.policies["Status"] == status]
        else:
            policies = self.policies

        if not policies.empty:
            # policy_type, sources, destinations, specifics
            return policies.apply(lambda row: Policy.get_policy(row.name[0], [row.name[3]], list(row["Destinations"]), row.name[2]), axis="columns").tolist()
        else:
            return list()

    def get_query(self, environment, group=False):
        policy_type, sources, destinations, specifics = self.get_raw_policy(status=PolicyStatus.UNKNOWN, group=group)
        query = Query(policy_type, sources, destinations, specifics, environment, negate=False)
        return query

    def get_source_counts(self, status=None):
        if not self.init:
            return None
        if status:
            raw_policies = self.policies[self.policies["Status"] == status]
        else:
            raw_policies = self.policies.iloc[0].name

        raw_group = raw_policies.groupby(["subnet"], sort=False).aggregate({"Sources": list})

        counts = dict()
        for index, row in raw_group.iterrows():
            sources = row.values[0]
            counts[index] = Counter(sources)

        return counts

    def trim_policies(self, k_connected_pairs):
        policy_count = 0

        policies = self.policies[self.policies["Status"] == PolicyStatus.UNKNOWN]
        for row in policies.iterrows():
            index = row[0]

            policy_type = index[0]
            src_router = index[3].router
            dst_subnet = index[1]
            specifics = index[2]

            destinations = row[1]["Destinations"]
            dst_routers = [destination.router for destination in destinations]

            if policy_type != PolicyType.Isolation:
                assert len(dst_routers) == 1, "There is more than one router connected to this subnet"
                dst_router = dst_routers[0]

                if src_router < dst_router:
                    pair = (src_router, dst_router)
                else:
                    pair = (dst_router, src_router)

                if pair not in k_connected_pairs:
                    self.policies.at[index, "Status"] = PolicyStatus.HOLDSNOT
                    policy_count += 1

        return policy_count

    def create_checkpoint(self):
        self.tmp_state = self.policies["Status"].copy()

    def restore_checkpoint(self):
        self.policies["Status"] = self.tmp_state

    def dump(self, file_path):
        self.policies.to_csv(file_path, index=True)
