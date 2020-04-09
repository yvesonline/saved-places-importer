# Saved Places Importer

## Synopsis

Google gives you the opportunity to download your data via [Google Takeout](https://en.wikipedia.org/wiki/Google_Takeout). But if you're moving accounts (e.g. from a free Google account to a paid Google account) there's no data importer for [Google Maps](http://maps.google.com) (at least to my knowledge). On top of this the Google Maps API is rather simple to non-existent when it comes to importing data, this means in order to get your **saved places** (the :star: you can set) back, you need to manually import them. This can get quite cumbersome if you have a lot of saved places. I wrote this script in order to help me batch import places I want to save, may it be from a previous backup or new ones. It's **highly experimental** and if you want to use it please use it at your own risk! I recently added an interactive mode because I was getting tired of clicking on the Web UI.

## Requirements

You will need to have Firefox installed and logged in to your Google account. Then you need the `marionette_driver` package which you can install via pip with `pip install marionette_driver`. Afterwards start your Firefox with `firefox -marionette` so that it can be controlled. Alternatively you can set `marionette.enabled` to `true` in `about:config`. If you don't want to temper with your system create a virtual environment using:
```lang=bash
$ virtualenv --version  # Check virtual environment is installed
$ virtualenv venv --python=python2.7  # Create a virtual environment
$ source venv/bin/activate  # Activate it...
$ pip install -r requirements.txt  # Install the requirements
$ deactivate  # Deactivate after you're done
```
Also make sure you have a file called `gm-api-key.json` in your root directory if you want to use the interactive mode. The file contains your Google Maps API key in the form of `{"key": "<your key here>"}`.

## Usage

```lang=bash
$ python2.7 spi.py --help
usage: spi.py [-h] {batch,interactive} ...

Saved Places Importer

positional arguments:
  {batch,interactive}
    batch              Batch mode, via import files
    interactive        Interactive mode, via menu

optional arguments:
  -h, --help           show this help message and exit
```

Examples:
```lang=bash
$ python2.7 spi.py interactive  # Interactive mode
$ python2.7 spi.py batch samples/sample-geo.json --dry-run  # Batch mode, import GeoJSON, only simulate
$ python2.7 spi.py batch samples/sample-geo.json --compare  # Batch mode, import GeoJSON, only compare
$ python2.7 spi.py batch samples/sample-geo.json  # Batch mode, import GeoJSON
```

## To-do list

- Combine common code from `interactive_loop_add_*`.
- Redesign entire application, especially sub-command structure.
- Add wait/throttling between requests.
- Reverse engineer actual API calls made by Google Maps to avoid Marionette?

## Issues

- No Python 3 support, [Marionette](https://pypi.org/project/marionette-driver/) is not compatible yet.

## Useful links

- [GeoJSON Wikipedia article](https://en.wikipedia.org/wiki/GeoJSON)
- [GPS Exchange Format Wikipedia article](https://en.wikipedia.org/wiki/GPS_Exchange_Format)
- [Archived Google Bookmarks API description](https://web.archive.org/web/20111206070337/http://www.mmartins.com/mmartins/googlebookmarksapi/)
- [marionette_driver package reference](https://firefox-source-docs.mozilla.org/python/marionette_driver.html)