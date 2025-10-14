from __future__ import annotations  # for forward references

from dataclasses import dataclass
from os import PathLike
from typing import List, Union, Any

from pykml import parser
from shapely.geometry import LineString, Point, Polygon


@dataclass
class kml_placemark:
    name: str
    geometry: Union[Point, LineString, Polygon]


@dataclass
class kml_folder:
    name: str
    folders: List[kml_folder]
    placemarks: List[kml_placemark]


class KMLParseError(Exception):
    """Exception for KML parsing errors."""

    pass


def parse_folder(folder: Any) -> kml_folder:
    folder_name = folder.name.text if hasattr(folder, "name") else "Unnamed Folder"
    placemarks = []

    for placemark in getattr(folder, "Placemark", []):
        name = (
            placemark.name.text if hasattr(placemark, "name") else "Unnamed Placemark"
        )
        geometry = None

        if hasattr(placemark, "Point"):
            # Disregard altitude if present
            coordinates = placemark.Point.coordinates.text.strip().split(",")[:2]
            geometry = Point(float(coordinates[0]), float(coordinates[1]))
        elif hasattr(placemark, "LineString"):
            coordinates = [
                tuple(map(float, coord.strip().split(","))[:2])
                for coord in placemark.LineString.coordinates.text.strip().split()
            ]
            geometry = LineString(coordinates)
        elif hasattr(placemark, "Polygon"):
            coordinates = [
                tuple(map(float, coord.strip().split(","))[:2])
                for coord in placemark.Polygon.outerBoundaryIs.LinearRing.coordinates.text.strip().split()
            ]
            coordinates.append(coordinates[0])  # Ensure the polygon is closed
            geometry = Polygon(coordinates)

        if geometry:
            placemarks.append(kml_placemark(name, geometry))

    child_folders = [parse_folder(child) for child in getattr(folder, "Folder", [])]

    return kml_folder(
        folder_name,
        folders=child_folders,
        placemarks=placemarks,
    )


def read_kml(kml_file: PathLike) -> kml_folder:
    with open(kml_file, "r", encoding="utf-8") as file:
        root = parser.parse(file).getroot()
        if not hasattr(root, "Document"):
            raise KMLParseError("KML file does not contain a Document element.")
        return parse_folder(root.Document)
