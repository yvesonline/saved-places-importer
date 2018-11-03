#!/usr/bin/env python2

import sys
import argparse
import json
import logging

from xml.etree.cElementTree import XML

from marionette_driver.marionette import Marionette
from marionette_driver import By, Wait, expected
from marionette_driver.errors import NoSuchElementException, TimeoutException


APP_NAME = "Saved Places Importer"

ADD_FEATURE_SUCCESS = 0
ADD_FEATURE_FAILURE = 1
ADD_FEATURE_ALREADY_ADDED = 2
ADD_FEATURE_UNKNOWN_ERROR = 3


def init_logging():
    """
    Initialize logging with a default level to INFO.
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
        Initialise the logger and the attribute.
        """
        self.logger = init_logging()
        # string to print in case a command finishes successfully
        self.success_symbol = u"\u2713"
        # string to print in case a command fails
        self.failure_symbol = u"\u2717"
        # the passed arguments
        self.import_file = args.import_file
        self.dry_run = args.dry_run
        self.compare = args.compare
        # Marionette
        self.client = None
        # Existing bookmarks LUT
        self.bookmarks = set()

    def init_ff(self):
        self.client = Marionette(host="localhost", port=2828)
        self.client.start_session()

    def get_existing_bookmarks(self):
        self.client.navigate("https://www.google.com/bookmarks/?output=xml&num=10000")
        root = XML(self.client.page_source.encode("utf-8"))
        for bookmark in root[0]:
            self.bookmarks.add(bookmark[1].text)

    def save_button_contains_correct_text_save(self, *args):
        save_button = self.client.find_element(By.CLASS_NAME, "section-entity-action-save-button")
        return save_button.text == "SAVE"

    def save_button_contains_correct_text_saved(self, *args):
        save_button = self.client.find_element(By.CLASS_NAME, "section-entity-action-save-button")
        return save_button.text == "SAVED"

    def add_feature(self, url):
        self.client.navigate(url)

        save_button = Wait(self.client, timeout=10).until(expected.element_present(By.CLASS_NAME, "section-entity-action-save-button"))

        displayed = Wait(self.client, timeout=10).until(expected.element_displayed(save_button))

        try:

            Wait(self.client, timeout=6).until(self.save_button_contains_correct_text_saved)

            return ADD_FEATURE_ALREADY_ADDED

        except TimeoutException:

            try:
                Wait(self.client, timeout=6).until(self.save_button_contains_correct_text_save)
                try:
                    save_button.click()
                except NoSuchElementException:
                    pass

                try:
                    Wait(self.client, timeout=4).until(self.save_button_contains_correct_text_saved)
                except TimeoutException:
                    save_button = self.client.find_element(By.CLASS_NAME, "section-entity-action-save-button")
                    self.logger.error(" > [ERROR] Save button didn't switch to 'SAVED', it contains '{}'".format(save_button.text))
                    return ADD_FEATURE_FAILURE

                return ADD_FEATURE_SUCCESS

            except TimeoutException:
                save_button = self.client.find_element(By.CLASS_NAME, "section-entity-action-save-button")
                self.logger.error(" > [ERROR] Save button contained unknown text '{}'".format(save_button.text))
                return ADD_FEATURE_UNKNOWN_ERROR

    def parse_geo_json(self):
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
        return []

    def process(self):
        # Start processing
        self.logger.info(u" > Start of {}".format(APP_NAME))
        self.logger.debug(u" > dry_run: {}".format(self.dry_run))
        self.logger.debug(u" > compare: {}".format(self.compare))
        self.logger.debug(u" > import_file: {}".format(self.import_file))

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
                self.logger.info(u" > [COMPARE] {:3d}/{} {}".format(i, num_features, feature))
                if feature in self.bookmarks:
                    nums["already_added"] += 1
            else:
                if feature not in self.bookmarks:
                    ret = self.add_feature(feature)
                else:
                    ret = ADD_FEATURE_ALREADY_ADDED

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
                self.logger.info(u" > {:3d}/{} {} {}".format(i, num_features, ret_string, feature))
            i += 1
        if not self.dry_run and not self.compare:
            self.logger.debug(u" > Summary:")
            self.logger.debug(u" > Success: {:3d}".format(nums["success"]))
            self.logger.debug(u" > Failure: {:3d}".format(nums["failure"]))
            self.logger.debug(u" > Already added: {:3d}".format(nums["already_added"]))
            self.logger.debug(u" > Unknown error: {:3d}".format(nums["unknown_error"]))
        elif self.compare:
            if nums["already_added"] == num_features:
                self.logger.debug(u" > All bookmarks / places already added / saved!")
            else:
                self.logger.debug(u" > {} bookmarks / places already added / saved".format(nums["already_added"]))
                self.logger.debug(u" > {} bookmarks / places need to be added / saved".format(num_features - nums["already_added"]))


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

# TODO
#
# Check if Marionette is installed?
# Check if `localhost` Marionette connection can be established?
# Add a `requirements.txt`
# Add a venv description?
# Write README (Synopsis, Requirements, Usage, `$ firefox -marionette`)
# Add inline documentation
# Add timing
# Add CSV reading
# Add wait / throttling between requests
# Refactor Marionette code to _not_ check if bookmark added (we do this elsewhere now)
# Reverse engineer actual API calls?
#
# URLs
#
# https://en.wikipedia.org/wiki/GeoJSON
# https://web.archive.org/web/20111206070337/http://www.mmartins.com/mmartins/googlebookmarksapi/
# https://marionette-client.readthedocs.io/en/latest/index.html
# https://www.google.com/bookmarks/
