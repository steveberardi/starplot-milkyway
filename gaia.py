import csv
import time
import json
from pathlib import Path
from multiprocessing import Pool

import numpy as np
from shapely import Polygon, from_wkb, Point
from astropy_healpix import HEALPix
from astropy import units as u

from starplot import MilkyWay, MapPlot, Miller, Mollweide, Robinson
from starplot.data import Catalog
from starplot.data.catalogs import BIG_SKY_MAG11
from starplot.data.stars import load
from starplot.styles import PlotStyle, extensions

__version__ = "0.2.0"

HERE = Path(__file__).resolve().parent
DATA_PATH = HERE / "data"
BUILD_PATH = HERE / "build"

gaia = Catalog(
    path=Path("data/gaia-18c") / "**" / "*.parquet",
    hive_partitioning=True,
    healpix_nside=4,
    spatial_query_method="healpix",
)

NSIDE = 32
NUM_WORKERS = 12

block_size = 4

hp = HEALPix(nside=NSIDE, order='nested')


def pixel_geometry(pixel) -> Polygon:
    """Returns shapely polygon of a healpix pixel"""
    lon, lat = hp.boundaries_lonlat([pixel], step=1)
    lon = lon.to(u.deg).value
    lat = lat.to(u.deg).value
    coordinates = np.vstack([lon.ravel(), lat.ravel()]).transpose()
    return Polygon(coordinates)

def count_stars(extent):
    stars = load(
        catalog=gaia, 
        # catalog=BIG_SKY_MAG11,
        extent=extent,
    )
    df = stars.to_pandas()
    return len(df)


def process_pixel(n):
    print(n)
    g = pixel_geometry(n)
    count = count_stars(g)
    ra = round(g.centroid.x, 2)
    dec = round(g.centroid.y, 2)
    return n, ra, dec, count, g

def build_pixel_map():
    pixels = [n for n in range(hp.npix)]
    
    with Pool(processes=NUM_WORKERS) as pool:
        results = pool.map(process_pixel, pixels) # [(n, ra, dec, count, geometry)]

    sorted_results = sorted(results, key=lambda r: (r[1], r[2]))
    
    print("Writing file...")
    with open(BUILD_PATH / f"pixels-{NSIDE}.csv", 'w') as pixelfile:
        writer = csv.writer(pixelfile)
        for n, ra, dec, count, geometry in sorted_results:
            writer.writerow([n, ra, dec, count, geometry.wkb])




def blocks():
    for r_block in np.arange(0, 360 + block_size, block_size):
        for d_block in np.arange(0, 180 + block_size/2, block_size/2):
            yield float(r_block), float(d_block)

def milky_ways():
    ctr = 0
    with open(DATA_PATH / "milkyway.json", "r") as infile:
        data = json.loads(infile.read())

        for feature in data["features"]:
            ctr += 1
            coordinates = feature["geometry"]["coordinates"]
            geometry = Polygon(coordinates[0])
            ra = round(geometry.centroid.x, 4)
            dec = round(geometry.centroid.y, 4)

            yield MilkyWay(
                pk=ctr,
                ra=ra,
                dec=dec,
                geometry=geometry,
            )





def build():
    print("Building Milky Way Catalog...")
    time_start = time.time()

    catalog = Catalog(path=BUILD_PATH / "milky_way.parquet")
    catalog.build(
        objects=milky_ways(),
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
    print(f"Done. {duration:.000f}s")


def create_map_of_pixels(threshold: int):
    import ast

    p = MapPlot(
        # ra_min=0,
        # ra_max=360,
        # dec_min=-75,
        # dec_max=75,
        projection=Robinson(),
        resolution=6_000,
        style=PlotStyle().extend(
            extensions.BLUE_NIGHT,
            extensions.MAP,
        )
    )

    with open(BUILD_PATH / f"pixels-{NSIDE}.csv", 'r') as pixelfile:
        reader = csv.reader(pixelfile)
        for n, ra, dec, count, wkb in reader:
            if int(count) > threshold:

                wkb_bytes = ast.literal_eval(wkb)
                p.circle(
                    center=(float(ra), float(dec)),
                    radius_degrees=1,
                    style__alpha=0.24,
                    style__color="white",
                )

    
    p.milky_way(style__alpha=1, style__edge_color="yellow", style__edge_width=4)
    p.export(BUILD_PATH / f"pixels-{NSIDE}.png", padding=0.5)




if __name__ == "__main__":

    # build_pixel_map()

    # 106.0215 , -5.3240  ( Monoceros )
    create_map_of_pixels(
        threshold=26_000,
    )