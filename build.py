import time
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from shapely import Polygon, box
from shapely.geometry import shape

from starplot import MapPlot, Mollweide, MilkyWay
from starplot.data import Catalog
from starplot.styles import PlotStyle, extensions


__version__ = "0.2.0"

HERE = Path(__file__).resolve().parent
DATA_PATH = HERE / "data"
BUILD_PATH = HERE / "build"

PARQUET_PATH = BUILD_PATH / f"milky_way-{__version__}.parquet"
STARS_IMAGE_PATH = DATA_PATH / "milkyway-mollweide.png"

# Size (degrees) of the grid cells used to chunk the Milky Way, and how far
# each chunk extends past its cell so that neighboring chunks overlap
CHUNK_SIZE = 8
CHUNK_OVERLAP = 0.5
# Chunks smaller than this (sq. degrees) are slivers at the edge of a cell
MIN_CHUNK_AREA = 0.1


def chunks(filename: str):
    with open(DATA_PATH / filename, "r") as infile:
        data = json.load(infile)

    for feature in data["features"]:
        yield from chunk_polygon(shape(feature["geometry"]))


def chunk_polygon(milky_way):
    min_x, min_y, max_x, max_y = milky_way.bounds

    x = min_x - (min_x % CHUNK_SIZE)
    while x < max_x:
        y = min_y - (min_y % CHUNK_SIZE)
        while y < max_y:
            cell = box(
                x - CHUNK_OVERLAP,
                y - CHUNK_OVERLAP,
                x + CHUNK_SIZE + CHUNK_OVERLAP,
                y + CHUNK_SIZE + CHUNK_OVERLAP,
            )
            piece = milky_way.intersection(cell)
            for polygon in getattr(piece, "geoms", [piece]):
                if isinstance(polygon, Polygon) and polygon.area >= MIN_CHUNK_AREA:
                    yield polygon
            y += CHUNK_SIZE
        x += CHUNK_SIZE


def milky_ways_chunked(filename: str):
    for pk, geometry in enumerate(chunks(filename), start=1):
        yield MilkyWay(
            pk=pk,
            ra=round(geometry.centroid.x, 4),
            dec=round(geometry.centroid.y, 4),
            geometry=geometry,
        )


def build(objects, path: Path, label: str):
    print(f"Building {label} Catalog...")
    time_start = time.time()

    catalog = Catalog(path=path)
    catalog.build(
        objects=objects,
        chunk_size=200_000,
        columns=[
            "pk",
            "ra",
            "dec",
            "geometry",
        ],
        partition_columns=[],
        compression="none",
        row_group_size=100_000,
    )

    duration = time.time() - time_start
    duration_ms = int(duration * 1000)
    print(f"Done. {duration_ms}ms")


def plot(catalog_path: Path, svg_path: Path):
    p = MapPlot(
        projection=Mollweide(),
        resolution=4_000,
        style=PlotStyle().extend(
            extensions.BLUE_NIGHT,
            extensions.MAP,
        ),
    )
    p.milky_way(catalog=Catalog(path=catalog_path))
    p.export(svg_path)


def mollweide_pixels(ra, dec, width, height):
    """Pixel position of RA/Dec in a Mollweide image centered on RA=180, with RA increasing to the left"""
    lam = -np.radians(np.asarray(ra) - 180)
    phi = np.radians(np.asarray(dec))
    theta = phi.copy()
    for _ in range(50):
        theta -= (2 * theta + np.sin(2 * theta) - np.pi * np.sin(phi)) / (
            2 + 2 * np.cos(2 * theta) + 1e-12
        )
    x = np.cos(theta) * lam / np.pi
    y = np.sin(theta)
    return (x * 0.5 + 0.5) * (width - 1), (0.5 - y * 0.5) * (height - 1)


def overlay(geojson_filename: str, image_path: Path, png_path: Path):
    """Draws a Milky Way polygon on top of a Mollweide image of the stars"""
    stars = Image.open(image_path).convert("RGBA")
    width, height = stars.size
    image = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    image.alpha_composite(stars)

    layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    with open(DATA_PATH / geojson_filename, "r") as infile:
        data = json.load(infile)

    for feature in data["features"]:
        polygon = shape(feature["geometry"])
        for ring, fill in [(polygon.exterior, (255, 60, 60, 70))] + [
            (hole, (0, 0, 0, 0)) for hole in polygon.interiors
        ]:
            coords = np.array(ring.coords)
            xs, ys = mollweide_pixels(coords[:, 0], coords[:, 1], width, height)
            points = list(zip(xs, ys))
            draw.polygon(points, fill=fill if fill[3] else None)
            draw.line(points + [points[0]], fill=(255, 220, 0, 255), width=2)

    image.alpha_composite(layer)
    image.convert("RGB").save(png_path)


if __name__ == "__main__":
    BUILD_PATH.mkdir(exist_ok=True)

    build(milky_ways_chunked("milkyway.json"), PARQUET_PATH, "Milky Way")
    plot(PARQUET_PATH, BUILD_PATH / f"milkyway-{__version__}.svg")
    overlay(
        "milkyway.json", STARS_IMAGE_PATH, BUILD_PATH / f"overlay-{__version__}.png"
    )
