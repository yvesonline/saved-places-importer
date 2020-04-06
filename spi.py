#!/usr/bin/env python2

import argparse
import logging
import json
import os
import urllib

import inquirer
import googlemaps

from utils.timing import Timing
from utils.marionette import MarionetteHelper
from utils.parse import parse_geo_json, parse_gpx
from utils.constants import APP_NAME, \
    LIST_STARRED_PLACES, LIST_WANT_TO_GO, \
    MODE_GPX, MODE_GEO_JSON, MODE_BATCH, MODE_INTERACTIVE


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
        self.import_file = args.import_file if "import_file" in args else ""
        self.dry_run = args.dry_run if "dry_run" in args else False
        self.compare = args.compare if "compare" in args else False
        self.list_add = args.list_add if "list_add" in args else None
        # The mode to operate in
        self.mode = MODE_BATCH if "import_file" in args else MODE_INTERACTIVE
        # The Marionette instance, wrapped by our own helper class
        self.marionette = MarionetteHelper(self.logger, self.success_symbol, self.failure_symbol)
        # A set of existing bookmarks to check later if a bookmark was already saved
        self.bookmarks = set()
        # Initialise Google Maps API
        try:
            path = os.path.dirname(os.path.realpath(__file__))
            key_file = "gm-api-key.json"
            with open("{}/{}".format(path, key_file), "r") as f:
                data = json.load(f)
                self.gm = googlemaps.Client(key=data["key"])
        except IOError:
            self.logger.error(
                u" > [ERROR] Unable to open '{}', Google Maps API disabled {}".format(
                        key_file, self.failure_symbol
                    )
            )
            self.gm = None
        # Initialise timing
        self.timing = Timing(self.logger)

    def interactive_loop(self):
        # Choices "Main Menu"
        # Add city
        # Exit
        choice = ""
        while choice != "Exit":
            choice = inquirer.list_input(
                "Please choose an action",
                choices=["Add city", "Exit"]
            )
            if choice == "Add city":
                self.interactive_loop_add_city()

    def interactive_loop_add_city(self):
        # Choices "Add city"
        # ...
        # Back
        choice = ""
        while choice != "Back":
            city = inquirer.text(message="Enter the name of the city to add")
            # Query for city
            gm_results = self.gm.places_autocomplete(
                input_text=city,
                types="(cities)"
            )
            # Let user choose which city to add
            choice = inquirer.list_input(
                "Please choose which city to add",
                choices=[(result["description"], result["place_id"]) for result in gm_results]
            )
            # Build Google Maps URL
            url = "https://www.google.com/maps/search/?{}"
            params = {
                "api": "1",
                "query": city,
                "query_place_id": choice,
            }
            self.logger.debug(u" > Google Maps URL: {}".format(url.format(urllib.urlencode(params))))
            # Navigate with Firefox and try to add
            self.marionette.add_feature_2(url.format(urllib.urlencode(params)), self.list_add)
            # Wait for user input
            choice = inquirer.list_input(
                "Please choose an action",
                choices=["Add another city", "Back"]
            )

    def process(self):
        # Start processing
        self.logger.info(u" > Start of {}".format(APP_NAME))
        self.logger.debug(u" > [ARGS] dry_run: {}".format(self.dry_run))
        self.logger.debug(u" > [ARGS] compare: {}".format(self.compare))
        self.logger.debug(u" > [ARGS] import_file: {}".format(self.import_file))
        self.logger.debug(u" > [ARGS] list_add: {}".format(self.list_add))

        # Check for interactive mode
        if self.mode == MODE_INTERACTIVE:
            self.logger.debug(u" > [ARGS] mode: {}".format(self.mode))
            self.marionette.init_ff()
            self.interactive_loop()
            exit(0)

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
                features = parse_geo_json(self.import_file)
            except IOError:
                self.logger.error(u" > [ERROR] Unable to open GeoJSON file '{}' {}".format(self.import_file, self.failure_symbol))
                exit(1)
            except ValueError as ve:
                self.logger.error(u" > [ERROR] {} {}".format(ve.message, self.failure_symbol))
                exit(1)

        # Parse GPX
        if self.import_file.endswith("gpx"):
            self.mode = MODE_GPX
            self.logger.debug(u" > [ARGS] mode: {}".format(self.mode))
            try:
                features = parse_gpx(self.import_file)
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
    subparsers = parser.add_subparsers()
    batch_mode_parser = subparsers.add_parser(
        "batch", help="Batch mode, via import files"
    )
    batch_mode_parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        default=False,
        help="whether or not to perform the actual import",
    )
    batch_mode_parser.add_argument(
        "--compare",
        action="store_true",
        dest="compare",
        default=False,
        help="only compare which bookmarks / places are already added / saved",
    )
    batch_mode_parser.add_argument(
        dest="import_file",
        default=None,
        help="the file to import (currently GeoJSON & GPX are supported)",
    )
    interactive_mode_parser = subparsers.add_parser(
        "interactive", help="Interactive mode, via menu"
    )
    interactive_mode_parser.add_argument(
        "--list",
        choices=[LIST_STARRED_PLACES, LIST_WANT_TO_GO],
        dest="list_add",
        default=LIST_STARRED_PLACES,
        help="which list to add bookmarks / places to"
    )

    # Parse the arguments
    args = parser.parse_args()

    # Hand over to helper class
    spi = SavedPlacesImporter(args)
    spi.process()
