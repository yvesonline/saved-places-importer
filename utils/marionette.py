#!/usr/bin/env python2

import sys

try:
    from marionette_driver.marionette import Marionette
    from marionette_driver import By, Wait, expected
    from marionette_driver.errors import NoSuchElementException, TimeoutException
except ImportError:
    sys.exit("Please install 'marionette_driver', e.g. with 'pip install marionette_driver'.")

from xml.etree.cElementTree import XML

from utils.net import check_socket
import utils.constants


MARIONETTE_HOST = "localhost"
MARIONETTE_PORT = 2828


class MarionetteHelper:

    def __init__(self, logger, success_symbol, failure_symbol):
        """
        Initialise the helper class.
        """
        self.client = None
        self.logger = logger
        self.success_symbol = success_symbol
        self.failure_symbol = failure_symbol

    def init_ff(self):
        """
        Initialises the connection to Firefox and starts a session.
        @return: -
        """
        if not check_socket(MARIONETTE_HOST, MARIONETTE_PORT):
            self.logger.error(
                u" > [ERROR] Please check if you started Firefox with the '-marionette' "
                "option or set 'marionette.enabled' to 'true' in 'about:config'. {}".format(self.failure_symbol)
            )
            sys.exit(1)
        self.client = Marionette(host=MARIONETTE_HOST, port=MARIONETTE_PORT)
        self.client.start_session()

    def get_existing_bookmarks(self):
        """
        Get the existing bookmarks from the Google Bookmarks API.
        We need to do this in Firefox to have the cookie set which authorities us with the API.
        @return: -
        """
        self.client.navigate("https://www.google.com/bookmarks/?output=xml&num=10000")
        # Initialise XML object
        root = XML(self.client.page_source.encode("utf-8"))
        # Return set of bookmarks
        return set([bookmark[1].text for bookmark in root[0]])

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

    def interactive_add_feature(self, coordinates):
        """
        Navigates to the Google Maps URL for the provided coordinates and waits for input.
        @return: -
        """
        url = "https://www.google.com/maps/search/?api=1&query={},{}"

        # This navigates Firefox to the passed URL
        self.client.navigate(url.format(coordinates[0], coordinates[1]))

        # Wait for input
        if sys.version_info[0] < 3:
            raw_input("Press Enter to continue...")
        else:
            input("Press Enter to continue...")

    def add_feature_2(self, url, list_add):
        """
        Tries to add a feature (bookmark / place) to your Google Maps fav list.
        @return: -
        """
        self.client.navigate(url)
        try:
            saved_button = Wait(self.client, timeout=1).until(
                expected.element_present(By.CSS_SELECTOR, "[data-value='Saved']")
            )
            self.logger.info(" > Feature was already saved")
            return utils.constants.ADD_FEATURE_ALREADY_ADDED
        except TimeoutException:
            pass
        try:
            save_button = Wait(self.client, timeout=5).until(
                expected.element_present(By.CSS_SELECTOR, "[data-value='Save']")
            )
            Wait(self.client, timeout=5).until(
                expected.element_displayed(save_button)
            )
        except TimeoutException:
            self.logger.error(" > Unable to find save button")
            return utils.constants.ADD_FEATURE_UNKNOWN_ERROR
        save_button.click()
        if list_add == utils.constants.LIST_STARRED_PLACES:
            data_index = 2
        elif list_add == utils.constants.LIST_WANT_TO_GO:
            data_index = 1
        else:
            data_index = -1
        css_selector = "#action-menu [data-index='{}']".format(data_index)
        sub_save_item = Wait(self.client, timeout=5).until(
            expected.element_present(By.CSS_SELECTOR, css_selector)
        )
        Wait(self.client, timeout=5).until(
            expected.element_displayed(sub_save_item)
        )
        sub_save_item.click()

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
            # So most likely something truly went wrong here.
            self.logger.error(" > [ERROR] Feature: '{}'".format(url))
            save_button = self.client.find_element(By.CLASS_NAME, "section-entity-action-save-button")
            self.logger.error(" > [ERROR] Save button contained unknown text '{}'".format(save_button.text))
            return ADD_FEATURE_UNKNOWN_ERROR
