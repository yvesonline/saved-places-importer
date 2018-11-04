#!/usr/bin/env python2

import time;

from functools import reduce


class Timing:
    """
    A class to help us time operations in the main scrop.
    It's able to track overall and interim times.
    """

    def __init__(self, logger):
        """
        Initialise the timing class, it expects a logger instance.
        """
        self.start = time.time()
        self.interim_counter = 0
        self.interim_times = {0: 0}
        self.logger = logger
        self.logger.debug(u" > [TIMING] Start: {:.6f}".format(self.start))

    def start_interim(self):
        """
        Start a new interim timer.
        @return: -
        """
        self.interim_times[self.interim_counter] = time.time()

    def stop_interim(self):
        """
        Stop the interim timer. It automatically increments the number of
        interims. Nested interims are currently _not_ supported.
        @return: -
        """
        self.interim_times[self.interim_counter] = time.time() - self.interim_times[self.interim_counter]
        self.logger.debug(u" > [TIMING] Interim: {:.6f}".format(self.interim_times[self.interim_counter]))
        self.interim_counter += 1

    def get_summary(self):
        """
        Stop the overall timer and print out a summary.
        @return: A dictionary containing the overall duration, an 
                 average of the interims and the number of interims.
        """
        self.stop = time.time()
        self.logger.debug(u" > [TIMING] Stop: {:.6f}".format(self.stop))
        times = {
            "total": self.stop - self.start,
            "interim_average": reduce((lambda x, y: x + y), self.interim_times.values()) / self.interim_counter if self.interim_counter > 0 else 0,
            "interim_counter": self.interim_counter
        }
        self.logger.info(u" > [TIMING] {:.6f} total time [s] elapsed".format(times["total"]))
        self.logger.info(u" > [TIMING] {:.6f} time [s] per bookmark / place".format(times["interim_average"]))
        return times
