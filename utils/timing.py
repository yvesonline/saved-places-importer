#!/usr/bin/env python2

import time;

from functools import reduce


class Timing:

    def __init__(self, logger):
        self.start = time.time()
        self.interim_counter = 0
        self.interim_times = {0: 0}
        self.logger = logger
        self.logger.debug(u" > [TIMING] Start: {:.2f}".format(self.start))

    def start_interim(self):
        self.interim_times[self.interim_counter] = time.time()

    def stop_interim(self):
        self.interim_times[self.interim_counter] = time.time() - self.interim_times[self.interim_counter]
        self.interim_counter += 1

    def get_summary(self):
        self.stop = time.time()
        self.logger.debug(u" > [TIMING] Stop: {:.2f}".format(self.stop))
        times = {
            "total": self.stop - self.start,
            "interim_average": reduce((lambda x, y: x + y), self.interim_times.values()) / self.interim_counter if self.interim_counter > 0 else 0,
            "interim_counter": self.interim_counter
        }
        self.logger.info(u" > [TIMING] {:.6f} total time [s] elapsed".format(times["total"]))
        self.logger.info(u" > [TIMING] {:.6f} time [s] per bookmark / place".format(times["interim_average"]))
        return times
