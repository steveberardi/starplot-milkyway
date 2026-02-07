import time
import json
from pathlib import Path

from shapely import Polygon

from starplot import MilkyWay
from starplot.data import Catalog


__version__ = "0.1.0"

HERE = Path(__file__).resolve().parent
DATA_PATH = HERE / "data"
BUILD_PATH = HERE / "build"

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


if __name__ == "__main__":
    build()
