#!/usr/bin/env python2

import argparse
import json
import logging

import xml.etree.ElementTree as ET

from utils.timing import Timing
from utils.marionette import MarionetteHelper


APP_NAME = "Saved Places Importer"

ADD_FEATURE_SUCCESS = 0
ADD_FEATURE_FAILURE = 1
ADD_FEATURE_ALREADY_ADDED = 2
ADD_FEATURE_UNKNOWN_ERROR = 3

MODE_GPX = "GPX"
MODE_GEO_JSON = "GEO_JSON"


def init_logging():
    """
    Initialize logging with a default level of INFO
    and do some basic configuration tasks.
    """
    logging.basicConfig(
        format="%(message)s",
        datefmt="",
        level=logging.DEBUG
    )
    logger = logging.getLogger()
    return logger


class SavedPlacesImporter:

    def __init__(self, args):
        """
        This initialises our main class, it expects
        the arguments to be passed in.
        """
        # Initialise the logger used throughout the whole script
        self.logger = init_logging()
        # String to print in case a command finishes successfully
        self.success_symbol = u"\u2713"
        # String to print in case a command fails
        self.failure_symbol = u"\u2717"
        # The passed arguments
        self.import_file = args.import_file
        self.dry_run = args.dry_run
        self.compare = args.compare
        # The mode to operate in
        self.mode = None
        # The Marionette instance, wrapped by our own helper class
        self.marionette = MarionetteHelper(self.logger, self.success_symbol, self.failure_symbol)
        # A set of existing bookmarks to check later if a bookmark was already saved
        self.bookmarks = set()
        # Initialise timing
        self.timing = Timing(self.logger)

    def parse_geo_json(self):
        """
        Parses a GeoJSON file and extracts the Google Maps URLs.
        @return: List of Google Maps URLs
        """
        with open(self.import_file, "r") as f:
            data = json.load(f)
        if "features" in data:
            urls = []
            for feature in data["features"]:
                assert "properties" in feature
                assert "Google Maps URL" in feature["properties"]
                urls.append(feature["properties"]["Google Maps URL"])
            return urls
        else:
            self.logger.error(u" > [ERROR] No 'features' key in GeoJSON found {}".format(self.failure_symbol))

    def parse_gpx(self):
        """
        Parses a GPX file.
        @return: List of Lat/Lon.
        """
        tree = ET.parse(self.import_file)
        name_tag = "{http://www.topografix.com/GPX/1/1}name"
        return [(wpt.attrib["lat"], wpt.attrib["lon"], wpt.find(name_tag).text) for wpt in tree.getroot()]

    def process(self):
        # Start processing
        self.logger.info(u" > Start of {}".format(APP_NAME))
        self.logger.debug(u" > [ARGS] dry_run: {}".format(self.dry_run))
        self.logger.debug(u" > [ARGS] compare: {}".format(self.compare))
        self.logger.debug(u" > [ARGS] import_file: {}".format(self.import_file))

        # Check arguments
        if not self.import_file.endswith("gpx") and not self.import_file.endswith("json"):
            self.logger.error(u" > [ERROR] Unknown file format supplied {}".format(self.failure_symbol))
            return
        if self.dry_run and self.compare:
            self.logger.error(u" > [ERROR] Please select either '--dry_run' or '--compare' {}".format(self.failure_symbol))
            return

        # Parse GeoJSON
        if self.import_file.endswith("json"):
            self.mode = MODE_GEO_JSON
            self.logger.debug(u" > [ARGS] mode: {}".format(self.mode))
            try:
                features = self.parse_geo_json()
            except IOError:
                self.logger.error(u" > [ERROR] Unable to open GeoJSON file '{}' {}".format(self.import_file, self.failure_symbol))
                exit(1)

        # Parse GPX
        if self.import_file.endswith("gpx"):
            self.mode = MODE_GPX
            self.logger.debug(u" > [ARGS] mode: {}".format(self.mode))
            try:
                features = self.parse_gpx()
            except IOError:
                self.logger.error(u" > [ERROR] Unable to open GPX file '{}' {}".format(self.import_file, self.failure_symbol))
                exit(1)

        # Check number of features returned
        num_features = len(features)
        if num_features == 0:
            self.logger.error(u" > [ERROR] No features to import found {}".format(self.failure_symbol))
        else:
            self.logger.info(u" > Found {} features to import {}".format(num_features, self.success_symbol))

        if not self.dry_run:
            self.marionette.init_ff()
            self.bookmarks = self.marionette.get_existing_bookmarks()
            self.logger.info(u" > Found {} existing bookmarks {}".format(len(self.bookmarks), self.success_symbol))

        # Add the features
        i = 1
        nums = {
            "success": 0,
            "failure": 0,
            "already_added": 0,
            "unknown_error": 0,
        }
        for feature in features:
            if self.dry_run:
                self.logger.info(u" > [DRY RUN] {:3d}/{} {}".format(i, num_features, feature))
            elif self.compare:
                if self.mode == MODE_GEO_JSON:
                    if feature in self.bookmarks:
                        nums["already_added"] += 1
                    else:
                        self.logger.info(u" > [COMPARE] {:3d}/{} {}".format(i, num_features, feature))
                elif self.mode == MODE_GPX:
                    self.logger.info(u" > [COMPARE] Compare not supported for GPX mode")
            else:
                if self.mode == MODE_GEO_JSON:
                    # Check if feature already exists, i.e. if the
                    # bookmark / place was already added previously
                    if feature not in self.bookmarks:
                        self.timing.start_interim()
                        ret = self.marionette.add_feature(feature)
                        self.timing.stop_interim()
                    else:
                        ret = ADD_FEATURE_ALREADY_ADDED
                    # Do some bookkeeping with the return value
                    if ret == ADD_FEATURE_SUCCESS:
                        ret_string = self.success_symbol
                        nums["success"] += 1
                    elif ret == ADD_FEATURE_FAILURE:
                        ret_string = self.failure_symbol
                        nums["failure"] += 1
                    elif ret == ADD_FEATURE_ALREADY_ADDED:
                        ret_string = u"-"
                        nums["already_added"] += 1
                    elif ret == ADD_FEATURE_UNKNOWN_ERROR:
                        ret_string = u"?"
                        nums["unknown_error"] += 1
                    self.logger.debug(u" > {:3d}/{} {} {}".format(i, num_features, ret_string, feature))
                elif self.mode == MODE_GPX:
                    self.logger.debug(u" > {:3d}/{} {}".format(i, num_features, feature))
                    self.marionette.interactive_add_feature(feature)
            i += 1
        if not self.dry_run and not self.compare:
            self.logger.info(u" > Summary:")
            self.logger.info(u" > Success: {:3d}".format(nums["success"]))
            self.logger.info(u" > Failure: {:3d}".format(nums["failure"]))
            self.logger.info(u" > Already added: {:3d}".format(nums["already_added"]))
            self.logger.info(u" > Unknown error: {:3d}".format(nums["unknown_error"]))
        elif self.compare:
            if nums["already_added"] == num_features:
                self.logger.info(u" > All bookmarks / places already added / saved!")
            else:
                self.logger.info(u" > {} bookmarks / places already added / saved".format(nums["already_added"]))
                self.logger.info(u" > {} bookmarks / places need to be added / saved".format(num_features - nums["already_added"]))
        self.timing.get_summary()


if __name__ == "__main__":
    # Declare the arguments
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description=APP_NAME)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        default=False,
        help="whether or not to perform the actual import",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        dest="compare",
        default=False,
        help="only compare which bookmarks / places are already added / saved",
    )
    parser.add_argument(
        dest="import_file",
        default=None,
        help="the file to import (currently GeoJSON & GPX are supported)",
    )

    # Parse the arguments
    args = parser.parse_args()

    # Hand over to helper class
    spi = SavedPlacesImporter(args)
    spi.process()
