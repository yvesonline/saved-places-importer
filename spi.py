#!/usr/bin/env python2

import sys
import argparse
import json
import logging

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
        # Marionette
        self.client = None

    def init_ff(self):
        self.client = Marionette(host="localhost", port=2828)
        self.client.start_session()

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
        self.logger.debug(u" > import_file: {}".format(self.import_file))

        # Check arguments
        if not self.import_file.endswith("csv") and not self.import_file.endswith("json"):
            self.logger.error(u" > [ERROR] Unknown file format supplied {}".format(self.failure_symbol))

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

        # Add the features
        i = 1
        for feature in urls:
            if self.dry_run:
                self.logger.info(u" > [DRY RUN] {:3d}/{} {}".format(i, num_features, feature))
            else:
                ret = self.add_feature(feature)
                if ret == ADD_FEATURE_SUCCESS:
                    ret_string = self.success_symbol
                elif ret == ADD_FEATURE_FAILURE:
                    ret_string = self.failure_symbol
                elif ret == ADD_FEATURE_ALREADY_ADDED:
                    ret_string = u"-"
                elif ret == ADD_FEATURE_UNKNOWN_ERROR:
                    ret_string = u"?"
                self.logger.info(u" > {:3d}/{} {} {}".format(i, num_features, ret_string, feature))
            i += 1


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
        dest="import_file",
        default=None,
        help="the file to import (currently GeoJSON & CSV are supported)",
    )

    # Parse the arguments
    args = parser.parse_args()

    # Hand over to helper class
    spi = SavedPlacesImporter(args)
    spi.process()

# TODO:
# Check for installed stuff!!!
# requirements.txt
# venv
# doc (synopsis, requirements)
# count how many were added / not added / failure
