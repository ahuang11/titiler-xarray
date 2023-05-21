import fsspec
import math
import random
import click
import morecantile
import numpy as np
import xarray as xr
import zarr
import csv

sources = url_dict = {
    "s3://veda-data-store-staging/EIS/zarr/FWI-GEOS-5-Hourly": {
        "collection_name": "FWI-GEOS-5-Hourly",
        "variable": "GEOS-5_FWI",
        "rescale": "0,40",
    },
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
    "https://ncsa.osn.xsede.org/Pangeo/pangeo-forge/pangeo-forge/aws-noaa-oisst-feedstock/aws-noaa-oisst-avhrr-only.zarr/reference.json": {
        "collection_name": "aws-noaa-oisst-avhrr-only",
        "variable": "sst",
        "rescale": "0,40",
        "reference": True,
        "drop_dim": "zlev",
        "drop_dim_value": 0
    },
    "s3://yuvipanda-test1/cmr/gpm3imergdl.zarr": {
        "collection_name": "gpm3imergdl",
        "variable": "precipitationCal",
        "rescale": "0,704"
    },
    "s3://nasa-eodc-zarrs/ames_research_center_fwi_monthly/fwi-kerchunk-reference.json": {
        "collection_name": "ames_research_center_fwi_monthly",
        "variable": "FWI",
        "reference": True,
        "anon": False,
        "rescale": "0.00001,107"
    }
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
maxzoom = 8
max_url = 10

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
csv_columns = [
    "source",
    "variable",
    "shape",
    "lat resolution",
    "lon resolution",
    "chunk shape",
    "chunk size mb",
    "compression"
]
# Write the information to the CSV file
with open(csv_file, "w", newline="") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
    writer.writeheader()

for key, value in sources.items():
    source = key
    variable = value["variable"]
    rescale = value["rescale"]
    collection_name = value["collection_name"]
    reference = value.get("reference", False)
    drop_dim = value.get("drop_dim", False)
    anon = value.get("anon", True)
    if reference:
        fs = fsspec.filesystem(
            "reference",
            fo=source,
            remote_options={"anon": anon},
        )
        src_path = fs.get_mapper("")        
        ds = xr.open_dataset(src_path, engine='zarr', consolidated=False, chunks='auto')
    else:
        ds = xr.open_dataset(source, engine='zarr', consolidated=True)    
    if drop_dim:
        ds = ds.sel({drop_dim: value['drop_dim_value']}).drop(drop_dim)
    var = ds[variable]
    shape = var.shape
    lat_resolution = np.diff(var["lat"].values).mean()
    lon_resolution = np.diff(var["lon"].values).mean()
    chunks = var.encoding.get("chunks", "N/A")
    dtype = var.encoding.get("dtype", "N/A")
    chunk_shape = str(chunks)
    chunk_size_mb = "N/A" if chunks is None else (np.prod(chunks) * dtype.itemsize)/1024/1024
    compression = var.encoding.get("compressor", "N/A")
    with open(csv_file, "a", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
        writer.writerow({
            "source": source,
            "variable": variable,
            "shape": shape,
            "lat resolution": lat_resolution,
            "lon resolution": lon_resolution,
            "chunk shape": chunk_shape,
            "chunk size mb": chunk_size_mb,
            "compression": compression,
        })

    with open(f"urls/{collection_name}_urls.txt", "w") as f:
        f.write("HOST=https://dev-titiler-xarray.delta-backend.com\n")
        f.write("PATH=tiles/\n")
        f.write("EXT=.png\n")
        f.write(f"QUERYSTRING=?reference={reference}&variable={variable}&rescale={rescale}&url={source}\n")    
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