# Performance tests

Commands below are run within this directory.

```bash
pip install locust locust-plugins
```

## Generating URLs to ets

Note: for the FWI-GEOS-5-Hourly dataset (or any dataset in veda-data-store and veda-data-store-staging), the `gen_test_urls.py` script requires data access via a role from the SMCE VEDA AWS account. Please skip this dataset or contact the SMCE team for access.

If you have role-based access to those buckets, you will need to assume the role using MFA and assume role, for example:

```bash
AWS_ACCOUNT_ID=XXX
AWS_USERNAME=XXX
aws sts assume-role --role-arn arn:aws:iam::${AWS_ACCOUNT_ID}:role/nasa-veda-prod --role-session-name aimees-session --serial-number arn:aws:iam::${AWS_ACCOUNT_ID}:mfa/${AWS_USERNAME} --token-code XXX
```

Then set the following environment variables:

```bash
AWS_ACCESS_KEY_ID=XXX
AWS_SECRET_ACCESS_KEY=XXX
AWS_SESSION_TOKEN=XXX
```

Otherwise, just comment out that dataset in the `gen_test_urls.py` script.

```bash
python gen_test_urls.py
```

## Run Locust

```bash
# public zarr
locust -i 1 -u 4 --urls-file=urls/CMIP6_GISS-E2-1-G_historical_urls.txt --csv=results/cmip6
locust -i 1 -u 4 --urls-file=urls/power_901_monthly_meteorology_utc_urls.txt --csv=results/power_meteorology
# https://dev-titiler-xarray.delta-backend.com/tiles/2/2/0.png?reference=False&variable=precipitationCal&rescale=0,704&url=s3://yuvipanda-test1/cmr/gpm3imergdl.zarr
locust -i 1 -u 4 --urls-file=urls/gpm3imergdl_urls.txt --csv=results/gpm3imergdl

# protected zarr
locust -i 1 -u 4 --urls-file=urls/FWI-GEOS-5-Hourly_urls.txt --csv=results/FWI-GEOS

# reference, public
locust -i 1 -u 4 --urls-file=urls/aws-noaa-oisst-avhrr-only_urls.txt --csv=results/noaa-oisst
# reference, protected
locust -i 1 -u 4 --urls-file=urls/ames_research_center_fwi_monthly_urls.txt --csv=results/ames_research_center_fwi_monthly
```

## Run siege

```bash
siege -f urls/CMIP6_GISS-E2-1-G_historical_urls.txt -c4 -r25 -l
siege -f urls/gpm3imergdl_urls.txt -c4 -r25 -l
```

## Read results

[`read-results.ipynb`](./read-results.ipynb) is a Jupyter notebook that reads the results CSV files.

