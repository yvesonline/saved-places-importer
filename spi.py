#!/usr/bin/env python2

import sys
import argparse
import json
import logging

from marionette_driver.marionette import Marionette
from marionette_driver import By, Wait, expected
from marionette_driver.errors import NoSuchElementException


APP_NAME = "Saved Places Importer"


def test():
    client = Marionette(host="localhost", port=2828)

    client.start_session()

    client.navigate("http://maps.google.com/?cid=17379504698839695744")

    save_button = Wait(client, timeout=10).until(expected.element_present(By.CLASS_NAME, "section-entity-action-save-button"))

    displayed = Wait(client, timeout=10).until(expected.element_displayed(save_button))

    print(save_button.text)

    try:
        save_button.click()
    except NoSuchElementException:
        pass

    print(save_button.text)


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
        # utf8
        #sys.setdefaultencoding("utf-8")
        # the passed arguments
        self.import_file = args.import_file
        self.dry_run = args.dry_run


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
            self.logger.error(u" > No features in GeoJSON found {}".format(self.failure_symbol))


    def parse_csv(self):
        return []

    def process(self):
        # Start processing
        self.logger.info(u" > Start of {}".format(APP_NAME))
        self.logger.debug(u" > dry_run: {}".format(self.dry_run))
        self.logger.debug(u" > import_file: {}".format(self.import_file))

        # Check arguments
        if not self.import_file.endswith("csv") and not self.import_file.endswith("json"):
            self.logger.error(u" > Unknown file format supplied {}".format(self.failure_symbol))

        # Parse GeoJSON
        if self.import_file.endswith("json"):
            urls = self.parse_geo_json()

        # Parse CSV
        if self.import_file.endswith("csv"):
            urls = self.parse_csv()

        # Check number of features returned
        num_features = len(urls)
        if num_features == 0:
            self.logger.error(u" > No features to import found {}".format(self.failure_symbol))
        else:
            self.logger.info(u" > Found {} features to import {}".format(num_features, self.success_symbol))


if __name__ == "__main__":
    # Declare the arguments
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description=APP_NAME)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        default=True,
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
# doc
