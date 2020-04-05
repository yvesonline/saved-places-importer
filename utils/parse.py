#!/usr/bin/env python2

import json

import xml.etree.ElementTree as ET


def parse_geo_json(import_file):
    """
    Parses a GeoJSON file and extracts the Google Maps URLs.
    @return: List of Google Maps URLs
    """
    with open(import_file, "r") as f:
        data = json.load(f)
    if "features" in data:
        urls = []
        for feature in data["features"]:
            assert "properties" in feature
            assert "Google Maps URL" in feature["properties"]
            urls.append(feature["properties"]["Google Maps URL"])
        return urls
    else:
        raise ValueError("No 'features' key in GeoJSON found")


def parse_gpx(import_file):
    """
    Parses a GPX file.
    @return: List of Lat/Lon.
    """
    tree = ET.parse(import_file)
    name_tag = "{http://www.topografix.com/GPX/1/1}name"
    return [(wpt.attrib["lat"], wpt.attrib["lon"], wpt.find(name_tag).text) for wpt in tree.getroot()]
