"""
geography.py - Helper functions for geographic calculations.
"""

from typing import Union, overload

import numpy as np

Number = Union[int, float, list, np.ndarray]


def tile2latlon(x: Number, y: Number, z: float) -> tuple[Number, Number]:
    """
    Convert tile coordinates to latitude and longitude.

    Parameters
    ----------
    x : Number
        Tile x-coordinate.
    y : Number
        Tile y-coordinate.
    z : float
        Zoom level.

    Returns
    -------
    lat, lon: tuple[Number, Number]
        Latitude and longitude(degrees).

    Notes
    -----
    Mathematics Reference: https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames#Mathematics
    """
    n = 2.0**z
    lon_deg = x / n * 360.0 - 180.0
    lat_rad = np.arctan(np.sinh(np.pi * (1 - 2 * y / n)))
    lat_deg = np.degrees(lat_rad)
    return lat_deg, lon_deg


def latlon2tile(lat: Number, lon: Number, z: Number) -> tuple[Number, Number]:
    """
    Convert latitude and longitude to tile coordinates.

    Parameters
    ----------
    lat : Number
        Latitude in degrees.
    lon : float
        Longitude in degrees.
    z : float
        Zoom level.

    Returns
    -------
    x, y: tuple
        Tile x and y coordinates.

    Notes
    -----
    Mathematics Reference: https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames#Mathematics
    """
    n = 2.0**z
    x = (lon + 180.0) / 360.0 * n
    lat_rad = np.radians(lat)
    y = (1.0 - np.log(np.tan(lat_rad) + 1.0 / np.cos(lat_rad)) / np.pi) / 2.0 * n
    return x, y


def calc_distance(lat1: Number, lon1: Number, lat2: Number, lon2: Number) -> Number:
    """
    Calculate the geodetic distance between two points on the Earth's surface.

    Parameters
    ----------
    lat1 : Number
        Latitude of the first point.
    lon1 : Number
        Longitude of the first point.
    lat2 : Number
        Latitude of the second point.
    lon2 : Number
        Longitude of the second point.

    Returns
    -------
    distance: float
        Distance between the two points in meters.

    Notes
    -----
    Mathematics Reference:
        - https://qiita.com/matsuda_tkm/items/4eba5632535ca2f699b4 (Qiita)
        - https://www2.nc-toyama.ac.jp/WEB_Profile/mkawai/lecture/sailing/geodetic/geosail.html (Original)
    """

    # GRS80 constants (JGD2011: GSI(https://www.gsi.go.jp/sokuchikijun/datum-main.html))
    f = 1.0 / 298.257222101  # Earth's flattening
    A = 6378_137.0  # Earth's semi-major axis in meters
    B = A * (1 - f)  # Earth's semi-minor axis in meters

    # Reduced latitude
    phi_1 = np.arctan2(B * np.tan(np.radians(lat1)), A)
    phi_2 = np.arctan2(B * np.tan(np.radians(lat2)), A)

    # spherical distance
    X = np.arccos(
        np.sin(phi_1) * np.sin(phi_2)
        + np.cos(phi_1) * np.cos(phi_2) * np.cos(np.radians(lon2 - lon1))
    )

    # Lambert-Andoyer correction
    Delta_rho = (
        f
        * (
            (np.sin(X) - X) * ((np.sin(phi_1) + np.sin(phi_2)) / np.cos(X / 2)) ** 2
            - (np.sin(X) + X) * ((np.sin(phi_1) - np.sin(phi_2)) / np.sin(X / 2)) ** 2
        )
        / 8
    )

    # Geodetic distance
    distance = A * (X + Delta_rho)

    return distance


def get_tile_urls(
    url: str, northwest: tuple[float, float], southeast: tuple[float, float], zoom: int
) -> list[list[str]]:
    """
    Get tile URLs for the specified area.

    Parameters
    ----------
    url : str
        URL of the tile server. {z}/{x}/{y} should be included.
    northwest : tuple[float, float]
        Latitude and longitude of the northwest corner.
    southeast : tuple[float, float]
        Latitude and longitude of the southeast corner.
    zoom : int
        Zoom level.

    Returns
    -------
    urls: list[list[str]]
        URLs of the tiles.
    """

    x1, y1 = latlon2tile(northwest[0], northwest[1], zoom)
    x2, y2 = latlon2tile(southeast[0], southeast[1], zoom)

    urls = []
    for y in range(int(y1), int(y2) + 1):
        row = []
        for x in range(int(x1), int(x2) + 1):
            row.append(url.format(z=zoom, x=x, y=y))
        urls.append(row)

    return urls


@overload
def get_px_in_meter(lat: float, lon: float, zoom: int) -> tuple[float, float]:
    """
    Calculate the size of the maptile pixel size in meters along the x and y axes.

    Parameters
    ----------
    lat : float
        Latitude of the tile.
    lon : float
        Longitude of the tile.
    zoom : int
        Zoom level.

    Returns
    -------
    px_w, px_h: tuple[float, float]
        Size of the pixel in meters along the x and y axes.
    """
    ...


@overload
def get_px_in_meter(x: float, y: float, zoom: int) -> tuple[float, float]:
    """
    Calculate the size of the maptile pixel size in meters along the x and y axes.

    Parameters
    ----------
    x : float
        x-coordinate of the tile.
    y : float
        y-coordinate of the tile.
    zoom : int
        Zoom level.

    Returns
    -------
    px_w, px_h: tuple[float, float]
        Size of the pixel in meters along the x and y axes.
    """
    ...


def get_px_in_meter(
    lat: float = None,
    lon: float = None,
    x: float = None,
    y: float = None,
    zoom: int = None,
) -> tuple[float, float]:

    if x is None and y is None:
        x, y = latlon2tile(lat, lon, zoom)
    elif lat is None and lon is None:
        lat, lon = tile2latlon(x, y, zoom)

    lat2, lon2 = tile2latlon(
        x + 1, y + 1, zoom
    )  # get the lat. and lon. of the tile next to the given tile

    px_w = calc_distance(lat, lon, lat, lon2) / 256
    px_h = calc_distance(lat, lon, lat2, lon) / 256

    return px_w, px_h
