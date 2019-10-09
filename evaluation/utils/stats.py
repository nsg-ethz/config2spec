#!/usr/bin/env python
# Author: Ruediger Birkner (Networked Systems Group at ETH Zurich)


class SamplingStats(object):
    def __init__(self, stime, guess_size, failed, sampling_time):
        self.time = stime
        self.guess_size = guess_size
        self.failed = failed
        self.sampling_time = sampling_time

    @staticmethod
    def get_heading():
        return "Guess Size, Time, Failed Sample, Sampling Time"

    def __str__(self):
        return "{size}, {time}, {fail}, {stime}".format(size=self.guess_size, time=self.time, fail=self.failed, stime=self.sampling_time)


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
        return "{size}, {nver}, {nvio}, {nunk}, {time}".format(size=self.query_size, nver=self.num_verified,
                                                               nvio=self.num_violated, nunk=self.num_unknown,
                                                               time=self.time)
