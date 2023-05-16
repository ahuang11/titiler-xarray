import math
import random
import click
import morecantile
import xarray as xr
import zarr
import csv

sources = url_dict = {
    # "s3://veda-data-store-staging/EIS/zarr/FWI-GEOS-5-Hourly": {
    #     "collection_name": "FWI-GEOS-5-Hourly",
    #     "variable": "GEOS-5_FWI",
    #     "rescale": "0,40",
    # },
    "s3://power-analysis-ready-datastore/power_901_monthly_meteorology_utc.zarr": {
        "collection_name": "power_901_monthly_meteorology_utc",
        "variable": "TS",
        "rescale": "200,300",
    },
    "s3://cmip6-pds/CMIP6/CMIP/NASA-GISS/GISS-E2-1-G/historical/r2i1p1f1/Amon/tas/gn/v20180827/": {
        "collection_name": "CMIP6_GISS-E2-1-G_historical",
        "variable": "tas",
        "rescale": "200,300",
    },
}

def _percentage_split(size, percentages):
    """Freely copied from TileSiege https://github.com/bdon/TileSiege"""
    prv = 0
    cumsum = 0.0
    for zoom, p in percentages.items():
        cumsum += p
        nxt = int(cumsum * size)
        yield zoom, prv, nxt
        prv = nxt

tms = morecantile.tms.get("WebMercatorQuad")

###########################################
# INPUTS

minzoom = 0
maxzoom = 5
max_url = 100

w, s, e, n  = bounds = [-180, -90, 180, 90]

###########################################
random.seed(3857)

distribution = [
    2,
    2,
    6,
    12,
    16,
    27,
    38,
    41,
    49,
    56,
    72,
    71,
    99,
    135,
    135,
    136,
    102,
    66,
    37,
    6,
    2 
]  # the total distribution...

total_weight = 0
extremas = {}
for zoom in range(minzoom, maxzoom + 1):
    total_weight = total_weight + distribution[zoom]
    ul_tile = tms.tile(w, n, zoom, truncate=True)
    lr_tile = tms.tile(e, s, zoom, truncate=True)

    minmax = tms.minmax(zoom)
    extremas[zoom] = {
        "x": {
            "min": max(ul_tile.x, minmax["x"]["min"]),
            "max": min(lr_tile.x, minmax["x"]["max"]),
        },
        "y": {
            "min": max(ul_tile.y, minmax["y"]["min"]),
            "max": min(lr_tile.y, minmax["y"]["max"]),
        },
    }


# Prepare the CSV file
csv_file = "zarr_info.csv"
csv_columns = ["Variable", "Chunk Shape", "Chunk Size", "Compression"]
# Write the information to the CSV file
with open(csv_file, "w", newline="") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
    writer.writeheader()
    #csv_file.close()

for key, value in sources.items():
    source = key
    variable = value["variable"]
    rescale = value["rescale"]
    collection_name = value["collection_name"]
    
    ds = xr.open_zarr(source, consolidated=True)    
    var = ds[variable]
    chunks = var.encoding.get("chunks", "N/A")
    chunk_shape = str(chunks)
    # Todo: don't think this is the right way to create the chunk size, need to get the data type
    chunk_size = "N/A" if chunks is None else str(sum(chunks))
    compression = var.encoding.get("compressor", "N/A")
    with open(csv_file, "a", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
        writer.writerow({
            "Variable": variable,
            "Chunk Shape": chunk_shape,
            "Chunk Size": chunk_size,
            "Compression": compression,
        })
        #csv_file.close()

    with open(f"{collection_name}_urls.txt", "w") as f:
        f.write("HOST=https://dev-titiler-xarray.delta-backend.com\n")
        f.write("PATH=tiles/\n")
        f.write("EXT=.png\n")
        f.write(f"QUERYSTRING=?variable={variable}&rescale={rescale}&url={source}\n")    
        rows = 0
        for zoom, start, end in _percentage_split(
            max_url,
            {
                zoom: distribution[zoom] / total_weight
                for zoom in range(minzoom, maxzoom + 1)
            },
        ):
            extrema = extremas[zoom]
            rows_for_zoom = end - start
            rows += rows_for_zoom
            for sample in range(rows_for_zoom):
                x = random.randint(extrema["x"]["min"], extrema["x"]["max"])
                y = random.randint(extrema["y"]["min"], extrema["y"]["max"])
                f.write(
                    f"$(HOST)/$(PATH){zoom}/{x}/{y}$(EXT)$(QUERYSTRING)\n"
                )

            if not "quiet":
                p1 = " " if zoom < 10 else ""
                p2 = " " * (len(str(10000)) - len(str(rows_for_zoom)))
                bar = "█" * math.ceil(rows_for_zoom / max_url * 60)
                click.echo(f"{p1}{zoom} | {p2}{rows_for_zoom} {bar}", err=True)