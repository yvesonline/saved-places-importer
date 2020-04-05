# Saved Places Importer

## Synopsis

Google gives you the opportunity to download your data via [Google Takeout](https://en.wikipedia.org/wiki/Google_Takeout). But if you're moving accounts (e.g. from a free Google account to a paid Google account) there's no data importer for [Google Maps](http://maps.google.com) (at least to my knowledge). On top of this the Google Maps API is rather simple to non-existent when it comes to importing data, this means in order to get your **saved places** (the :star: you can set) back, you need to manually import them. This can get quite cumbersome if you have a lot of saved places. I wrote this script in order to help me batch import places I want to save, may it be from a previous backup or new ones. It's **highly experimental** and if you want to use it please use it at your own risk!

## Requirements

You will need to have Firefox installed and logged in to your Google account. Then you need the `marionette_driver` package which you can install via pip with `pip install marionette_driver`. Afterwards start your Firefox with `firefox -marionette` so that it can be controlled. Alternatively you can set `marionette.enabled` to `true` in `about:config`. If you don't want to temper with your system create a virtual environment using:
```lang=bash
$ virtualenv --version  # Check virtual environment is installed
$ virtualenv venv --python=python2.7  # Create a virtual environment
$ source venv/bin/activate  # Activate it...
$ pip install -r requirements.txt  # Install the requirements
$ deactivate  # Deactivate after you're done
```

## Usage

```lang=bash
$ python2.7 spi.py --help
usage: spi.py [-h] [--dry-run] [--compare] import_file

Saved Places Importer

positional arguments:
  import_file  the file to import (currently GeoJSON & CSV are supported)

optional arguments:
  -h, --help   show this help message and exit
  --dry-run    whether or not to perform the actual import
  --compare    only compare which bookmarks / places are already added / saved
```

Examples:
```lang=bash
$ python2.7 spi.py samples/sample-geo.json --dry-run
$ python2.7 spi.py samples/sample-geo.json --compare
$ python2.7 spi.py samples/sample-geo.json
```

## To-do list

- Add wait / throttling between requests.
- Reverse engineer actual API calls made by Google Maps?

## Issues

- No Python 3 support, [Marionette](https://pypi.org/project/marionette-driver/) is not compatible yet.

## Useful links

- [GeoJSON Wikipedia article](https://en.wikipedia.org/wiki/GeoJSON)
- [GPS Exchange Format Wikipedia article](https://en.wikipedia.org/wiki/GPS_Exchange_Format)
- [Archived Google Bookmarks API description](https://web.archive.org/web/20111206070337/http://www.mmartins.com/mmartins/googlebookmarksapi/)
- [Marionette reference](https://marionette-client.readthedocs.io/en/latest/index.html)