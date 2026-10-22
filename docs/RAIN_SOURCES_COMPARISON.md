# IMERG, ERA5 and NASA POWER rainfall comparison

IMERG raw NetCDF files were inspected read-only. A metadata/hash sidecar was written to `data/raw/weather/imerg/DOWNLOAD_LOG.txt`; source rasters were not changed.

## IMERG file inventory and metadata

Files inventoried: **86**. Product: `GPM IMERG Final Precipitation L3 1 day 0.1 degree x 0.1 degree (GPM_3IMERGDF)`. Variable `precipitation`; the local files omit a `units` attribute, but the NASA GES DISC collection documentation defines this daily product field as a daily mean precipitation rate in **mm/day** (mean valid half-hourly rate multiplied by 24). Version inferred from product title/file version: V07B; NetCDF dimensions [('time', 1), ('lon', 3600), ('lat', 1800)]; dtype float32; grid CF longitude/latitude coordinate axes at 0.1° spacing (GDAL does not expose a raster CRS or affine transform for these NetCDF coordinates). Product DOI: 10.5067/GPM/IMERGDF/DAY/07. See [NASA GES DISC product documentation](https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGDF_07/summary?keywords=IMERG+Final).
The files contain daily UTC (00:00–23:59:59.999 UTC) values. Longitude coordinate values are approximately −179.95° to 179.95° and latitude −89.95° to 89.95°, each increasing by 0.1°. The script reads only the small time/lon/lat slice around the CMA using the NetCDF C API and takes the unweighted mean of 0.1° pixel centres contained by the boundary. This coarse-grid method is approximate, especially along the boundary. Product metadata identifies daily mean precipitation rate in mm/day; it is not direct gauge accumulation.

### Event windows

| Window | Expected files | Present | Missing dates |
|---|---:|---:|---|
| 2015 | 45 | 45 | None |
| 2021 | 20 | 20 | None |
| 2023 | 21 | 21 | None |

### Daily CMA means

| Date (UTC) | IMERG (mm/day) | ERA5 point mean (UTC date, mm) | NASA POWER mean (UTC, mm/day) |
|---|---:|---:|---:|
| 2015-11-01 | 27.205 | 20.122 | 19.313 |
| 2015-11-02 | 4.400 | 5.100 | 12.432 |
| 2015-11-03 | 9.875 | 9.044 | 11.098 |
| 2015-11-04 | 0.013 | 7.478 | 2.561 |
| 2015-11-05 | 0.248 | 1.456 | 1.038 |
| 2015-11-06 | 0.394 | 4.511 | 4.264 |
| 2015-11-07 | 5.301 | 6.989 | 15.238 |
| 2015-11-08 | 116.570 | 77.022 | 79.858 |
| 2015-11-09 | 35.784 | 46.622 | 130.842 |
| 2015-11-10 | 10.202 | 5.200 | 31.606 |
| 2015-11-11 | 21.120 | 17.967 | 32.588 |
| 2015-11-12 | 55.059 | 16.267 | 34.667 |
| 2015-11-13 | 70.502 | 17.789 | 19.653 |
| 2015-11-14 | 13.977 | 3.433 | 21.539 |
| 2015-11-15 | 233.363 | 64.722 | 121.083 |
| 2015-11-16 | 41.355 | 93.644 | 104.756 |
| 2015-11-17 | 2.300 | 0.000 | 15.093 |
| 2015-11-18 | 2.788 | 14.033 | 24.170 |
| 2015-11-19 | 32.065 | 32.967 | 40.471 |
| 2015-11-20 | 13.922 | 8.511 | 16.477 |
| 2015-11-21 | 6.281 | 9.311 | 13.963 |
| 2015-11-22 | 38.531 | 16.367 | 72.840 |
| 2015-11-23 | 28.169 | 11.611 | 45.389 |
| 2015-11-24 | 0.000 | 0.611 | 0.050 |
| 2015-11-25 | 0.098 | 1.811 | 0.613 |
| 2015-11-26 | 1.976 | 0.933 | 22.091 |
| 2015-11-27 | 0.000 | 0.000 | 1.742 |
| 2015-11-28 | 2.559 | 1.978 | 8.654 |
| 2015-11-29 | 10.622 | 17.733 | 47.058 |
| 2015-11-30 | 50.060 | 32.211 | 64.673 |
| 2015-12-01 | 264.777 | 43.978 | 118.729 |
| 2015-12-02 | 36.705 | 54.600 | 35.821 |
| 2015-12-03 | 4.395 | 12.222 | 22.703 |
| 2015-12-04 | 1.266 | 8.222 | 17.876 |
| 2015-12-05 | 4.298 | 10.311 | 15.926 |
| 2015-12-06 | 6.215 | 11.789 | 11.041 |
| 2015-12-07 | 0.000 | 0.033 | 1.012 |
| 2015-12-08 | 0.560 | 4.489 | 1.657 |
| 2015-12-09 | 0.024 | 11.611 | 2.790 |
| 2015-12-10 | 0.000 | 1.167 | 0.216 |
| 2015-12-11 | 0.000 | 1.578 | 0.037 |
| 2015-12-12 | 0.185 | 0.000 | 0.000 |
| 2015-12-13 | 0.019 | 0.000 | 0.000 |
| 2015-12-14 | 0.010 | 0.000 | 0.000 |
| 2015-12-15 | 0.000 | 0.000 | 0.000 |
| 2021-11-01 | 45.734 | 20.111 | 22.223 |
| 2021-11-02 | 36.755 | 14.033 | 22.631 |
| 2021-11-03 | 50.402 | 16.689 | 27.643 |
| 2021-11-04 | 32.741 | 7.511 | 20.251 |
| 2021-11-05 | 7.389 | 20.556 | 18.236 |
| 2021-11-06 | 24.937 | 34.289 | 54.180 |
| 2021-11-07 | 44.994 | 28.011 | 36.301 |
| 2021-11-08 | 46.927 | 18.978 | 24.436 |
| 2021-11-09 | 14.925 | 13.222 | 18.236 |
| 2021-11-10 | 104.650 | 120.878 | 95.438 |
| 2021-11-11 | 19.854 | 40.667 | 68.096 |
| 2021-11-12 | 1.389 | 0.200 | 3.909 |
| 2021-11-13 | 1.028 | 4.600 | 3.514 |
| 2021-11-14 | 1.847 | 25.044 | 4.731 |
| 2021-11-15 | 11.187 | 3.100 | 3.008 |
| 2021-11-16 | 1.378 | 10.244 | 2.276 |
| 2021-11-17 | 29.390 | 46.133 | 28.842 |
| 2021-11-18 | 22.814 | 50.289 | 61.690 |
| 2021-11-19 | 7.854 | 5.022 | 10.853 |
| 2021-11-20 | 17.688 | 9.556 | 11.318 |
| 2023-11-25 | 5.778 | 5.811 | 5.670 |
| 2023-11-26 | 20.134 | 4.278 | 10.644 |
| 2023-11-27 | 1.879 | 6.100 | 13.380 |
| 2023-11-28 | 5.034 | 4.156 | 23.859 |
| 2023-11-29 | 27.770 | 18.456 | 37.984 |
| 2023-11-30 | 10.078 | 16.878 | 22.946 |
| 2023-12-01 | 2.518 | 2.956 | 14.189 |
| 2023-12-02 | 23.655 | 21.311 | 35.954 |
| 2023-12-03 | 105.714 | 74.311 | 87.718 |
| 2023-12-04 | 149.705 | 184.656 | 165.520 |
| 2023-12-05 | 5.618 | 1.022 | 4.452 |
| 2023-12-06 | 0.702 | 2.278 | 3.284 |
| 2023-12-07 | 0.263 | 4.022 | 1.026 |
| 2023-12-08 | 0.126 | 2.989 | 0.534 |
| 2023-12-09 | 0.034 | 0.633 | 0.268 |
| 2023-12-10 | 0.000 | 0.000 | 0.144 |
| 2023-12-11 | 0.016 | 0.667 | 0.103 |
| 2023-12-12 | 0.000 | 0.800 | 0.119 |
| 2023-12-13 | 0.000 | 0.633 | 0.037 |
| 2023-12-14 | 0.001 | 0.467 | 0.901 |
| 2023-12-15 | 3.053 | 7.500 | 6.696 |

### Event peaks and matched-day agreement

#### 2015
- IMERG peak: 2015-12-01 at 264.777 mm/day.
- IMERG event-window daily mean: 25.626 mm/day across 45 available days.
- ERA5 peak: 2015-11-16 at 93.644 mm/day.
- ERA5 event-window daily mean: 15.677 mm/day across 45 available days.
- NASA POWER peak: 2015-11-09 at 130.842 mm/day.
- NASA POWER event-window daily mean: 27.636 mm/day across 45 available days.
| Pair | n matched days | Pearson r | Bias (first minus second, mm/day) |
|---|---:|---:|---:|
| IMERG–ERA5 | 45 | 0.6398 | 9.950 |
| IMERG–NASA POWER | 45 | 0.7544 | -2.010 |
| ERA5–NASA POWER | 45 | 0.8296 | -11.960 |
#### 2021
- IMERG peak: 2021-11-10 at 104.650 mm/day.
- IMERG event-window daily mean: 26.194 mm/day across 20 available days.
- ERA5 peak: 2021-11-10 at 120.878 mm/day.
- ERA5 event-window daily mean: 24.457 mm/day across 20 available days.
- NASA POWER peak: 2021-11-10 at 95.438 mm/day.
- NASA POWER event-window daily mean: 26.891 mm/day across 20 available days.
| Pair | n matched days | Pearson r | Bias (first minus second, mm/day) |
|---|---:|---:|---:|
| IMERG–ERA5 | 20 | 0.7376 | 1.738 |
| IMERG–NASA POWER | 20 | 0.7019 | -0.696 |
| ERA5–NASA POWER | 20 | 0.8802 | -2.434 |
#### 2023
- IMERG peak: 2023-12-04 at 149.705 mm/day.
- IMERG event-window daily mean: 17.242 mm/day across 21 available days.
- ERA5 peak: 2023-12-04 at 184.656 mm/day.
- ERA5 event-window daily mean: 17.139 mm/day across 21 available days.
- NASA POWER peak: 2023-12-04 at 165.520 mm/day.
- NASA POWER event-window daily mean: 20.735 mm/day across 21 available days.
| Pair | n matched days | Pearson r | Bias (first minus second, mm/day) |
|---|---:|---:|---:|
| IMERG–ERA5 | 21 | 0.9616 | 0.103 |
| IMERG–NASA POWER | 21 | 0.9755 | -3.493 |
| ERA5–NASA POWER | 21 | 0.9784 | -3.596 |

## Does a source capture 1–2 Dec 2015?

Daily values for UTC 1–2 December are shown below; the event totals straddle local/UTC calendar boundaries, so compare timestamps cautiously. ERA5 hourly records were converted from their explicit `timestamp_utc` field and grouped into UTC dates, matching IMERG and NASA POWER UTC-day labels. IMERG shows the strongest 1 Dec daily estimate (264.777 mm/day), compared with 118.729 for NASA POWER and 43.978 for ERA5; this suggests IMERG captures the rain pulse more strongly in that UTC bucket, but does not establish which estimate is closest to gauge truth.

| Date UTC | IMERG | ERA5 | NASA POWER |
|---|---:|---:|---:|
| 2015-12-01 | 264.777 | 43.978 | 118.729 |
| 2015-12-02 | 36.705 | 54.600 | 35.821 |

No source here is gauge truth; all are gridded or model-derived estimates.
