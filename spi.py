#!/usr/bin/env python2

import sys
import argparse
import json
import logging

from xml.etree.cElementTree import XML

try:
    from marionette_driver.marionette import Marionette
    from marionette_driver import By, Wait, expected
    from marionette_driver.errors import NoSuchElementException, TimeoutException
except ImportError:
    sys.exit("Please install 'marionette_driver', e.g. with 'pip install marionette_driver'.")

from utils.timing import Timing
from utils.net import check_socket


APP_NAME = "Saved Places Importer"

ADD_FEATURE_SUCCESS = 0
ADD_FEATURE_FAILURE = 1
ADD_FEATURE_ALREADY_ADDED = 2
ADD_FEATURE_UNKNOWN_ERROR = 3

MARIONETTE_HOST = "localhost"
MARIONETTE_PORT = 2828


def init_logging():
    """
    Initialize logging with a default level of INFO
    and do some basic configuration tasks.
    """
    logging.basicConfig(
        format="%(message)s",
        datefmt="",
        level=logging.INFO
    )
    logger = logging.getLogger()
    return logger


class SavedPlacesImporter:

    def __init__(self, args):
        """
        This inits our main class, it expects
        the arguments to be passed in.
        """
        # Init the logger used throughout the whole script
        self.logger = init_logging()
        # String to print in case a command finishes successfully
        self.success_symbol = u"\u2713"
        # String to print in case a command fails
        self.failure_symbol = u"\u2717"
        # The passed arguments
        self.import_file = args.import_file
        self.dry_run = args.dry_run
        self.compare = args.compare
        # The Marionette instance
        self.client = None
        # A set of existing bookmarks to check later if a bookmark was already saved
        self.bookmarks = set()
        # Initialise timing
        self.timing = Timing(self.logger)

    def init_ff(self):
        """
        Initialises the connection to Firefox and starts a session.
        @return: -
        """
        if not check_socket(MARIONETTE_HOST, MARIONETTE_PORT):
            self.logger.error(u" > [ERROR] Please check if you started Firefox with the '-marionette' option. {}".format(self.failure_symbol))
            sys.exit(1)
        self.client = Marionette(host=MARIONETTE_HOST, port=MARIONETTE_PORT)
        self.client.start_session()

    def get_existing_bookmarks(self):
        """
        Get the existing bookmarks from the Google Bookmarks API.
        We need to do this in Firefox to have the cookie set which authorises us with the API.
        @return: -
        """
        self.client.navigate("https://www.google.com/bookmarks/?output=xml&num=10000")
        # Initialise XML object
        root = XML(self.client.page_source.encode("utf-8"))
        # Add existing bookmarks to our set of bookmarks
        for bookmark in root[0]:
            self.bookmarks.add(bookmark[1].text)

    def save_button_contains_correct_text_save(self, *args):
        """
        Helper method for Marionette, here: check if fav button contains text "SAVE"
        @return: Whether or not the fav button contains the text "SAVE"
        """
        save_button = self.client.find_element(By.CLASS_NAME, "section-entity-action-save-button")
        return save_button.text == "SAVE"

    def save_button_contains_correct_text_saved(self, *args):
        """
        Helper method for Marionette, here: check if fav button contains text "SAVED"
        @return: Whether or not the fav button contains the text "SAVED"
        """
        save_button = self.client.find_element(By.CLASS_NAME, "section-entity-action-save-button")
        return save_button.text == "SAVED"

    def add_feature(self, url):
        """
        Tries to add a feature (bookmark / place) to your Google Maps fav list.
        @return:
        - ADD_FEATURE_FAILURE if adding resulted in a known failure
        - ADD_FEATURE_SUCCESS if everything went fine
        - ADD_FEATURE_UNKNOWN_ERROR if we don't know what happened
        """

        # This navigates Firefox to the passed URL
        self.client.navigate(url)

        # We wait for the fav button to be present...
        save_button = Wait(self.client, timeout=10).until(expected.element_present(By.CLASS_NAME, "section-entity-action-save-button"))

        # ... and to be displayed
        displayed = Wait(self.client, timeout=10).until(expected.element_displayed(save_button))

        try:
            # Now we look for the correct text, it should say "SAVE"
            Wait(self.client, timeout=6).until(self.save_button_contains_correct_text_save)
            try:
                # Click it to add the feature (bookmark / place) to the Google Maps fav list
                save_button.click()
            except NoSuchElementException:
                pass

            try:
                # Now the text should be "SAVED" and this indicates it was saved
                Wait(self.client, timeout=6).until(self.save_button_contains_correct_text_saved)
            except TimeoutException:
                # We clicked but the fav button text didn't change, i.e. the click went wrong or timed out
                self.logger.error(" > [ERROR] Feature: '{}'".format(url))
                save_button = self.client.find_element(By.CLASS_NAME, "section-entity-action-save-button")
                self.logger.error(" > [ERROR] Save button didn't switch to 'SAVED', it contains '{}'".format(save_button.text))
                return ADD_FEATURE_FAILURE

            return ADD_FEATURE_SUCCESS

        except TimeoutException:
            # This is the case if the fave button didn't contain the text "SAVE".
            # This can happen if it contains "SAVED", but this shouldn't happen in the
            # first place because we don't try to add features if we know that they're
            # already added.
            # So most likely something truely went wrong here.
            self.logger.error(" > [ERROR] Feature: '{}'".format(url))
            save_button = self.client.find_element(By.CLASS_NAME, "section-entity-action-save-button")
            self.logger.error(" > [ERROR] Save button contained unknown text '{}'".format(save_button.text))
            return ADD_FEATURE_UNKNOWN_ERROR

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

    def parse_csv(self):
        """
        Parses a CSV file and tries to look up Google Maps URLs.
        Currently unimplemented!
        @return: List of Google Maps URLs
        """
        return []

    def process(self):
        # Start processing
        self.logger.info(u" > Start of {}".format(APP_NAME))
        self.logger.debug(u" > [ARGS] dry_run: {}".format(self.dry_run))
        self.logger.debug(u" > [ARGS] compare: {}".format(self.compare))
        self.logger.debug(u" > [ARGS] import_file: {}".format(self.import_file))

        # Check arguments
        if not self.import_file.endswith("csv") and not self.import_file.endswith("json"):
            self.logger.error(u" > [ERROR] Unknown file format supplied {}".format(self.failure_symbol))
            return
        if self.dry_run and self.compare:
            self.logger.error(u" > [ERROR] Please select either '--dry_run' or '--compare' {}".format(self.failure_symbol))
            return

        # Parse GeoJSON
        if self.import_file.endswith("json"):
            urls = self.parse_geo_json()

        # Parse CSV
        if self.import_file.endswith("csv"):
            urls = self.parse_csv()

        # Check number of features returned
        num_features = len(urls)
        if num_features == 0:
            self.logger.error(u" > [ERROR] No features to import found {}".format(self.failure_symbol))
        else:
            self.logger.info(u" > Found {} features to import {}".format(num_features, self.success_symbol))

        if not self.dry_run:
            self.init_ff()

        if not self.dry_run:
            self.get_existing_bookmarks()
            self.logger.info(u" > Found {} existing bookmarks {}".format(len(self.bookmarks), self.success_symbol))

        # Add the features
        i = 1
        nums = {
            "success": 0,
            "failure": 0,
            "already_added": 0,
            "unknown_error": 0,
        }
        for feature in urls:
            if self.dry_run:
                self.logger.info(u" > [DRY RUN] {:3d}/{} {}".format(i, num_features, feature))
            elif self.compare:
                if feature in self.bookmarks:
                    nums["already_added"] += 1
                else:
                    self.logger.info(u" > [COMPARE] {:3d}/{} {}".format(i, num_features, feature))
            else:
                # Check if feature already exists, i.e. if the
                # bookmark / place was already added previously
                if feature not in self.bookmarks:
                    self.timing.start_interim()
                    ret = self.add_feature(feature)
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
        help="the file to import (currently GeoJSON & CSV are supported)",
    )

    # Parse the arguments
    args = parser.parse_args()

    # Hand over to helper class
    spi = SavedPlacesImporter(args)
    spi.process()
