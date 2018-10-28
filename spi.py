#!/usr/bin/python2

import sys
import argparse

from marionette_driver.marionette import Marionette
from marionette_driver import By, Wait, expected
from marionette_driver.errors import NoSuchElementException

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

if __name__ == "__main__":
    # Declare arguments
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description="Saved Places Importer")
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

    # Check arguments
    if not args.import_file.endswith("csv") and not args.import_file.endswith("json"):
        sys.exit("Unknown file format supplied")
