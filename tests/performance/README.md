# Performance tests

Commands below are run within this directory.

## Generating URLs to ets

Note: for the FWI-GEOS-5-Hourly dataset (or any dataset in veda-data-store and veda-data-store-staging), the `gen_test_urls.py` script requires data access via a role from the SMCE VEDA AWS account. Please skip this dataset or contact the SMCE team for access.

If you have role-based access to those buckets, you will need to assume the role using MFA and assume role, for example:

```bash
aws sts assume-role --role-arn arn:aws:iam::XXX:role/nasa-veda-prod --role-session-name aimees-session --serial-number arn:aws:iam::XXX:mfa/username --token-code 000000
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
locust --urls-file=urls/CMIP6_GISS-E2-1-G_historical_urls.txt --csv=results/cmip6
locust --urls-file=urls/aws-noaa-oisst-avhrr-only_urls.txt --csv=results/noaa-oisst
locust --urls-file=urls/FWI-GEOS-5-Hourly_urls.txt --csv=results/FWI-GEOS
locust --urls-file=urls/power_901_monthly_meteorology_utc_urls.txt --csv=results/power_meteorology
```

## Read results

[`read-results.ipynb`](./read-results.ipynb) is a Jupyter notebook that reads the results CSV files.

