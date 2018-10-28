from marionette_driver.marionette import Marionette
from marionette_driver import By, Wait, expected
from marionette_driver.errors import NoSuchElementException

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
