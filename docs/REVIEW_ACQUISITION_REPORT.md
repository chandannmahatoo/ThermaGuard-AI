# Final live-state addendum — 11 September 2026

After the controlled acquisition finished and the API was restored, the server received live FIRMS sync, threshold-change and alert-acknowledgement requests that this task did not issue. Those later changes are preserved. The controlled collection results and integrity checks remain a point-in-time record in the next section; they must not be confused with the final live database. Model V1 files still match the pre-task hashes.

**Final observed live state: 790 real detections, 405 real events, 405 canonical candidates, 372 unreviewed candidates / evidence packets, 33 preserved review claims, 0 V2-eligible reviews. MODEL_V2_READY = false.**

This task acquired 530 observations / 264 net events without alerts. The later live sync added another 139 S-NPP NRT observations / 108 net events. The database now contains five alerts including the original demo alert; four were created outside the controlled acquisition. All 33 original real event payloads were subsequently refreshed by live activity. Human CSV cells remain preserved, but 24 reviews now differ from stored evidence (23 at the controlled checkpoint). Do not restore or overwrite those live changes automatically.

| FIRMS source | Stored observations | Event memberships | Claimed reviewed | V2 eligible | Date range |
|---|---:|---:|---:|---:|---|
| VIIRS_SNPP_NRT | 274 | 151 | 33 | 0 | 2026-06-03 – 2026-09-11 |
| VIIRS_NOAA20_NRT | 41 | 33 | 0 | 0 | 2026-06-01 – 2026-09-10 |
| VIIRS_NOAA21_NRT | 37 | 29 | 0 | 0 | 2026-06-01 – 2026-09-09 |
| MODIS_NRT | 17 | 10 | 0 | 0 | 2026-05-01 – 2026-06-05 |
| VIIRS_SNPP_SP | 342 | 148 | 0 | 0 | 2026-04-23 – 2026-04-27 |
| VIIRS_NOAA20_SP | 31 | 26 | 0 | 0 | 2026-05-27 – 2026-05-31 |
| MODIS_SP | 48 | 24 | 0 | 0 | 2026-04-26 – 2026-04-30 |
| unknown_legacy | 0 | 0 | 0 | 0 | — – — |

## Final event source combinations

| Combination | Events |
|---|---:|
| VIIRS_SNPP_NRT | 147 |
| VIIRS_NOAA20_NRT | 28 |
| VIIRS_NOAA20_SP | 26 |
| VIIRS_NOAA20_NRT + VIIRS_NOAA21_NRT + VIIRS_SNPP_NRT | 3 |
| VIIRS_SNPP_SP | 140 |
| MODIS_SP | 16 |
| MODIS_SP + VIIRS_SNPP_SP | 8 |
| MODIS_NRT | 10 |
| VIIRS_NOAA20_NRT + VIIRS_SNPP_NRT | 1 |
| VIIRS_NOAA20_NRT + VIIRS_NOAA21_NRT | 1 |
| VIIRS_NOAA21_NRT | 25 |

## Final sensor combinations

| Combination | Events |
|---|---:|
| SNPP | 287 |
| NOAA20 | 54 |
| NOAA20 + NOAA21 + SNPP | 3 |
| MODIS | 26 |
| MODIS + SNPP | 8 |
| NOAA20 + SNPP | 1 |
| NOAA20 + NOAA21 | 1 |
| NOAA21 | 25 |

Final satellite counts: {'N': 616, 'N20': 72, 'N21': 37, 'Aqua': 64, 'Terra': 1}. Instruments: {'VIIRS': 725, 'MODIS': 65}. Processing kinds: {'nrt_only': 215, 'sp_only': 190}.
Cross-sensor events: 14; reviewed: 0. Reviewed class × sensor matrix and 13 claimed split groups are unchanged from the controlled snapshot below.

Final quality: zero duplicate candidate/provider IDs, conflicting labels, exact NRT/SP copies, invalid observations, missing provenance, or exact-overpass split conflicts. The 58 nearby-site split warnings persist. All 33 legacy reviews still lack timestamps; strict eligibility is zero for every class/source.

## Final missing-feature profile

Cells show missing event memberships / total memberships. The following tables supersede the controlled-snapshot missingness tables below.


### All real events

| Field | all |
|---|---:|
| frp | 0 / 405 |
| primary_thermal | 0 / 405 |
| secondary_thermal | 0 / 405 |
| ndvi | 373 / 405 |
| osm_context | 365 / 405 |
| historical_recurrence | 0 / 405 |
| viirs_snpp_count | 0 / 405 |
| viirs_noaa20_count | 0 / 405 |
| viirs_noaa21_count | 0 / 405 |
| modis_count | 0 / 405 |
| independent_detection_count | 0 / 405 |
| nrt_sp_representation_count | 0 / 405 |
| unique_instrument_count | 0 / 405 |
| viirs_frp_mean | 26 / 405 |
| viirs_frp_max | 26 / 405 |
| modis_frp_mean | 371 / 405 |
| modis_frp_max | 371 / 405 |
| day_detection_fraction | 0 / 405 |
| night_detection_fraction | 0 / 405 |
| cross_sensor_confirmed | 0 / 405 |
| viirs_primary_thermal_mean | 26 / 405 |
| viirs_secondary_thermal_mean | 26 / 405 |
| modis_primary_thermal_mean | 371 / 405 |
| modis_secondary_thermal_mean | 371 / 405 |

### By sensor

| Field | SNPP | NOAA20 | NOAA21 | MODIS |
|---|---:|---:|---:|---:|
| frp | 0 / 299 | 0 / 59 | 0 / 29 | 0 / 34 |
| primary_thermal | 0 / 299 | 0 / 59 | 0 / 29 | 0 / 34 |
| secondary_thermal | 0 / 299 | 0 / 59 | 0 / 29 | 0 / 34 |
| ndvi | 271 / 299 | 57 / 59 | 28 / 29 | 31 / 34 |
| osm_context | 261 / 299 | 58 / 59 | 28 / 29 | 32 / 34 |
| historical_recurrence | 0 / 299 | 0 / 59 | 0 / 29 | 0 / 34 |
| viirs_snpp_count | 0 / 299 | 0 / 59 | 0 / 29 | 0 / 34 |
| viirs_noaa20_count | 0 / 299 | 0 / 59 | 0 / 29 | 0 / 34 |
| viirs_noaa21_count | 0 / 299 | 0 / 59 | 0 / 29 | 0 / 34 |
| modis_count | 0 / 299 | 0 / 59 | 0 / 29 | 0 / 34 |
| independent_detection_count | 0 / 299 | 0 / 59 | 0 / 29 | 0 / 34 |
| nrt_sp_representation_count | 0 / 299 | 0 / 59 | 0 / 29 | 0 / 34 |
| unique_instrument_count | 0 / 299 | 0 / 59 | 0 / 29 | 0 / 34 |
| viirs_frp_mean | 0 / 299 | 0 / 59 | 0 / 29 | 26 / 34 |
| viirs_frp_max | 0 / 299 | 0 / 59 | 0 / 29 | 26 / 34 |
| modis_frp_mean | 291 / 299 | 59 / 59 | 29 / 29 | 0 / 34 |
| modis_frp_max | 291 / 299 | 59 / 59 | 29 / 29 | 0 / 34 |
| day_detection_fraction | 0 / 299 | 0 / 59 | 0 / 29 | 0 / 34 |
| night_detection_fraction | 0 / 299 | 0 / 59 | 0 / 29 | 0 / 34 |
| cross_sensor_confirmed | 0 / 299 | 0 / 59 | 0 / 29 | 0 / 34 |
| viirs_primary_thermal_mean | 0 / 299 | 0 / 59 | 0 / 29 | 26 / 34 |
| viirs_secondary_thermal_mean | 0 / 299 | 0 / 59 | 0 / 29 | 26 / 34 |
| modis_primary_thermal_mean | 291 / 299 | 59 / 59 | 29 / 29 | 0 / 34 |
| modis_secondary_thermal_mean | 291 / 299 | 59 / 59 | 29 / 29 | 0 / 34 |

### By source

| Field | VIIRS_SNPP_NRT | VIIRS_NOAA20_NRT | VIIRS_NOAA21_NRT | MODIS_NRT | VIIRS_SNPP_SP | VIIRS_NOAA20_SP | MODIS_SP | unknown_legacy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| frp | 0 / 151 | 0 / 33 | 0 / 29 | 0 / 10 | 0 / 148 | 0 / 26 | 0 / 24 | N/A (0 events) |
| primary_thermal | 0 / 151 | 0 / 33 | 0 / 29 | 0 / 10 | 0 / 148 | 0 / 26 | 0 / 24 | N/A (0 events) |
| secondary_thermal | 0 / 151 | 0 / 33 | 0 / 29 | 0 / 10 | 0 / 148 | 0 / 26 | 0 / 24 | N/A (0 events) |
| ndvi | 129 / 151 | 31 / 33 | 28 / 29 | 9 / 10 | 142 / 148 | 26 / 26 | 22 / 24 | N/A (0 events) |
| osm_context | 118 / 151 | 32 / 33 | 28 / 29 | 9 / 10 | 143 / 148 | 26 / 26 | 23 / 24 | N/A (0 events) |
| historical_recurrence | 0 / 151 | 0 / 33 | 0 / 29 | 0 / 10 | 0 / 148 | 0 / 26 | 0 / 24 | N/A (0 events) |
| viirs_snpp_count | 0 / 151 | 0 / 33 | 0 / 29 | 0 / 10 | 0 / 148 | 0 / 26 | 0 / 24 | N/A (0 events) |
| viirs_noaa20_count | 0 / 151 | 0 / 33 | 0 / 29 | 0 / 10 | 0 / 148 | 0 / 26 | 0 / 24 | N/A (0 events) |
| viirs_noaa21_count | 0 / 151 | 0 / 33 | 0 / 29 | 0 / 10 | 0 / 148 | 0 / 26 | 0 / 24 | N/A (0 events) |
| modis_count | 0 / 151 | 0 / 33 | 0 / 29 | 0 / 10 | 0 / 148 | 0 / 26 | 0 / 24 | N/A (0 events) |
| independent_detection_count | 0 / 151 | 0 / 33 | 0 / 29 | 0 / 10 | 0 / 148 | 0 / 26 | 0 / 24 | N/A (0 events) |
| nrt_sp_representation_count | 0 / 151 | 0 / 33 | 0 / 29 | 0 / 10 | 0 / 148 | 0 / 26 | 0 / 24 | N/A (0 events) |
| unique_instrument_count | 0 / 151 | 0 / 33 | 0 / 29 | 0 / 10 | 0 / 148 | 0 / 26 | 0 / 24 | N/A (0 events) |
| viirs_frp_mean | 0 / 151 | 0 / 33 | 0 / 29 | 10 / 10 | 0 / 148 | 0 / 26 | 16 / 24 | N/A (0 events) |
| viirs_frp_max | 0 / 151 | 0 / 33 | 0 / 29 | 10 / 10 | 0 / 148 | 0 / 26 | 16 / 24 | N/A (0 events) |
| modis_frp_mean | 151 / 151 | 33 / 33 | 29 / 29 | 0 / 10 | 140 / 148 | 26 / 26 | 0 / 24 | N/A (0 events) |
| modis_frp_max | 151 / 151 | 33 / 33 | 29 / 29 | 0 / 10 | 140 / 148 | 26 / 26 | 0 / 24 | N/A (0 events) |
| day_detection_fraction | 0 / 151 | 0 / 33 | 0 / 29 | 0 / 10 | 0 / 148 | 0 / 26 | 0 / 24 | N/A (0 events) |
| night_detection_fraction | 0 / 151 | 0 / 33 | 0 / 29 | 0 / 10 | 0 / 148 | 0 / 26 | 0 / 24 | N/A (0 events) |
| cross_sensor_confirmed | 0 / 151 | 0 / 33 | 0 / 29 | 0 / 10 | 0 / 148 | 0 / 26 | 0 / 24 | N/A (0 events) |
| viirs_primary_thermal_mean | 0 / 151 | 0 / 33 | 0 / 29 | 10 / 10 | 0 / 148 | 0 / 26 | 16 / 24 | N/A (0 events) |
| viirs_secondary_thermal_mean | 0 / 151 | 0 / 33 | 0 / 29 | 10 / 10 | 0 / 148 | 0 / 26 | 16 / 24 | N/A (0 events) |
| modis_primary_thermal_mean | 151 / 151 | 33 / 33 | 29 / 29 | 0 / 10 | 140 / 148 | 26 / 26 | 0 / 24 | N/A (0 events) |
| modis_secondary_thermal_mean | 151 / 151 | 33 / 33 | 29 / 29 | 0 / 10 | 140 / 148 | 26 / 26 | 0 / 24 | N/A (0 events) |

### By claimed reviewed class

| Field | industrial_fire | persistent_industrial_thermal_source | agricultural_vegetation_fire | natural_thermal_event | possible_false_positive |
|---|---:|---:|---:|---:|---:|
| frp | 0 / 6 | 0 / 6 | 0 / 7 | 0 / 5 | 0 / 9 |
| primary_thermal | 0 / 6 | 0 / 6 | 0 / 7 | 0 / 5 | 0 / 9 |
| secondary_thermal | 0 / 6 | 0 / 6 | 0 / 7 | 0 / 5 | 0 / 9 |
| ndvi | 4 / 6 | 2 / 6 | 2 / 7 | 0 / 5 | 3 / 9 |
| osm_context | 0 / 6 | 0 / 6 | 0 / 7 | 0 / 5 | 0 / 9 |
| historical_recurrence | 0 / 6 | 0 / 6 | 0 / 7 | 0 / 5 | 0 / 9 |
| viirs_snpp_count | 0 / 6 | 0 / 6 | 0 / 7 | 0 / 5 | 0 / 9 |
| viirs_noaa20_count | 0 / 6 | 0 / 6 | 0 / 7 | 0 / 5 | 0 / 9 |
| viirs_noaa21_count | 0 / 6 | 0 / 6 | 0 / 7 | 0 / 5 | 0 / 9 |
| modis_count | 0 / 6 | 0 / 6 | 0 / 7 | 0 / 5 | 0 / 9 |
| independent_detection_count | 0 / 6 | 0 / 6 | 0 / 7 | 0 / 5 | 0 / 9 |
| nrt_sp_representation_count | 0 / 6 | 0 / 6 | 0 / 7 | 0 / 5 | 0 / 9 |
| unique_instrument_count | 0 / 6 | 0 / 6 | 0 / 7 | 0 / 5 | 0 / 9 |
| viirs_frp_mean | 0 / 6 | 0 / 6 | 0 / 7 | 0 / 5 | 0 / 9 |
| viirs_frp_max | 0 / 6 | 0 / 6 | 0 / 7 | 0 / 5 | 0 / 9 |
| modis_frp_mean | 6 / 6 | 6 / 6 | 7 / 7 | 5 / 5 | 9 / 9 |
| modis_frp_max | 6 / 6 | 6 / 6 | 7 / 7 | 5 / 5 | 9 / 9 |
| day_detection_fraction | 0 / 6 | 0 / 6 | 0 / 7 | 0 / 5 | 0 / 9 |
| night_detection_fraction | 0 / 6 | 0 / 6 | 0 / 7 | 0 / 5 | 0 / 9 |
| cross_sensor_confirmed | 0 / 6 | 0 / 6 | 0 / 7 | 0 / 5 | 0 / 9 |
| viirs_primary_thermal_mean | 0 / 6 | 0 / 6 | 0 / 7 | 0 / 5 | 0 / 9 |
| viirs_secondary_thermal_mean | 0 / 6 | 0 / 6 | 0 / 7 | 0 / 5 | 0 / 9 |
| modis_primary_thermal_mean | 6 / 6 | 6 / 6 | 7 / 7 | 5 / 5 | 9 / 9 |
| modis_secondary_thermal_mean | 6 / 6 | 6 / 6 | 7 / 7 | 5 / 5 | 9 / 9 |

## Final verification and interpretation

The authenticated browser successfully loaded both pages of the raw-observation endpoint and displayed **RAW · 790 / 790**. The dashboard had previously shown the controlled 297-event / 651-detection state before the later live sync. Raw mode has a distinct instrument legend and disables the event risk filter. No live sync, threshold change or alert acknowledgement was issued by this verification.

Backend regressions: 194 passed; frontend API: 12 passed; typecheck and production build passed. Project virtual-environment pip check and compile checks passed. System Python pip check remains unhealthy (certifi/rpds-py/cffi missing). There is no standalone frontend lint script. The CSV CRLF-aware diff check passes.

The Model V2 scientific limits below remain: no genuine new reviews, all reviewed evidence S-NPP-only, severe source/region imbalance, missing context, and unresolved facility-group leakage. Current missingness takes precedence over the controlled checkpoint values. No training, commit or push was performed.

---

# Controlled acquisition checkpoint (before subsequent live activity)
# Multi-source Model V2 acquisition audit — 11 September 2026

**Actual collection completed; MODEL_V2_READY = false.** 530 real observations were added, increasing the real dataset from 121 detections / 33 events to 651 detections / 297 events. There are 264 new unreviewed candidate events and 264 evidence packets. No labels were created, no model was trained, and no alerts were generated.

## 1–3. Supported, stored, and reviewed sources

All seven sources below are supported and now actually stored. Events can belong to several sources; event memberships must not be added as independent training samples. All 33 existing claimed reviews are S-NPP NRT; strict V2 eligibility is zero for every source.

| Source | Detections | Event memberships | Claimed reviewed | V2 eligible | Stored date range |
|---|---:|---:|---:|---:|---|
| VIIRS_SNPP_NRT | 135 | 43 | 33 | 0 | 2026-06-03 – 2026-09-10 |
| VIIRS_NOAA20_NRT | 41 | 33 | 0 | 0 | 2026-06-01 – 2026-09-10 |
| VIIRS_NOAA21_NRT | 37 | 29 | 0 | 0 | 2026-06-01 – 2026-09-09 |
| MODIS_NRT | 17 | 10 | 0 | 0 | 2026-05-01 – 2026-06-05 |
| VIIRS_SNPP_SP | 342 | 148 | 0 | 0 | 2026-04-23 – 2026-04-27 |
| VIIRS_NOAA20_SP | 31 | 26 | 0 | 0 | 2026-05-27 – 2026-05-31 |
| MODIS_SP | 48 | 24 | 0 | 0 | 2026-04-26 – 2026-04-30 |
| unknown_legacy | 0 | 0 | 0 | 0 | — – — |

Stored event source combinations:

| Source combination | Events |
|---|---:|
| VIIRS_SNPP_NRT | 39 |
| VIIRS_NOAA20_NRT | 28 |
| VIIRS_NOAA20_SP | 26 |
| VIIRS_NOAA20_NRT + VIIRS_NOAA21_NRT + VIIRS_SNPP_NRT | 3 |
| VIIRS_SNPP_SP | 140 |
| MODIS_SP | 16 |
| MODIS_SP + VIIRS_SNPP_SP | 8 |
| MODIS_NRT | 10 |
| VIIRS_NOAA20_NRT + VIIRS_SNPP_NRT | 1 |
| VIIRS_NOAA20_NRT + VIIRS_NOAA21_NRT | 1 |
| VIIRS_NOAA21_NRT | 25 |

Processing kinds: {'nrt_only': 107, 'sp_only': 190}. Reviewed processing kinds: {'nrt_only': 33}. There are no mixed NRT/SP events in this collection.

Demo isolation: 10 detections and 4 events remain unchanged and are excluded from the 651 / 297 real totals. The one pre-existing demo alert is unchanged.

## 4. Legacy reconciliation

Applied: **121 resolved, 0 unresolved, 0 ambiguous**. Of these, 69 had a stored acquisition query identifying VIIRS_SNPP_NRT; 52 had mutually consistent raw satellite N, instrument VIIRS and version 2.0NRT. Raw coordinates/time/platform identity were validated against the normalized observation before updating provenance. The resolver refuses conflicts, missing evidence and unrecognized platforms. Existing IDs, raw provider fields, measurements and event payloads were preserved.

The interpretation uses NASA’s documented platform/version fields, including N = S-NPP and the NRT version suffix. Current FIRMS documentation also records the NOAA-20/21 satellite aliases. Sources: [NASA fire-detection training material](https://disasters.nasa.gov/sites/default/files/2023-03/D1P5_FireDetection_Final.pdf), [FIRMS active-fire documentation](https://firms.modaps.eosdis.nasa.gov/active_fire/).

## 5. Actual bounded acquisition

Availability metadata was fetched before each plan. Three sequential plans used 7, 7 and 5 area requests (19 total), each no more than the configured 12-request budget. All windows were five days; no worldwide query or truncated response was used. Each plan ran under the existing in-process ingestion lock while the separate API process was paused. Network calls occurred outside database transactions. Every response was validated; all 530 returned rows were accepted, with zero rejected. Empty MODIS September results were retained honestly before trying metadata-valid earlier windows.

| Region | Source | Start | Days | Received | Accepted | Rejected | New events | Reclustered old unreviewed IDs removed |
|---|---|---|---:|---:|---:|---:|---:|---:|
| jamnagar_coastal_refinery | MODIS_NRT | 2026-09-07 | 5 | 0 | 0 | 0 | 0 | 0 |
| jamnagar_coastal_refinery | MODIS_SP | 2026-04-26 | 5 | 0 | 0 | 0 | 0 | 0 |
| jamnagar_coastal_refinery | VIIRS_NOAA20_NRT | 2026-09-07 | 5 | 3 | 3 | 0 | 2 | 0 |
| jamnagar_coastal_refinery | VIIRS_NOAA20_SP | 2026-05-27 | 5 | 8 | 8 | 0 | 6 | 0 |
| jamnagar_coastal_refinery | VIIRS_NOAA21_NRT | 2026-09-07 | 5 | 2 | 2 | 0 | 1 | 0 |
| jamnagar_coastal_refinery | VIIRS_SNPP_NRT | 2026-09-07 | 5 | 3 | 3 | 0 | 0 | 1 |
| jamnagar_coastal_refinery | VIIRS_SNPP_SP | 2026-04-23 | 5 | 2 | 2 | 0 | 1 | 0 |
| bastar_forest_mining | MODIS_NRT | 2026-09-07 | 5 | 0 | 0 | 0 | 0 | 0 |
| bastar_forest_mining | MODIS_SP | 2026-04-26 | 5 | 48 | 48 | 0 | 25 | 0 |
| bastar_forest_mining | VIIRS_NOAA20_NRT | 2026-09-07 | 5 | 0 | 0 | 0 | 0 | 0 |
| bastar_forest_mining | VIIRS_NOAA20_SP | 2026-05-27 | 5 | 23 | 23 | 0 | 20 | 0 |
| bastar_forest_mining | VIIRS_NOAA21_NRT | 2026-09-07 | 5 | 0 | 0 | 0 | 0 | 0 |
| bastar_forest_mining | VIIRS_SNPP_NRT | 2026-09-07 | 5 | 0 | 0 | 0 | 0 | 0 |
| bastar_forest_mining | VIIRS_SNPP_SP | 2026-04-23 | 5 | 340 | 340 | 0 | 147 | 9 |
| punjab_agricultural_plains | MODIS_NRT | 2026-06-01 | 5 | 2 | 2 | 0 | 2 | 0 |
| punjab_agricultural_plains | VIIRS_NOAA20_NRT | 2026-06-01 | 5 | 38 | 38 | 0 | 31 | 0 |
| punjab_agricultural_plains | VIIRS_NOAA21_NRT | 2026-06-01 | 5 | 35 | 35 | 0 | 25 | 0 |
| punjab_agricultural_plains | VIIRS_SNPP_NRT | 2026-06-01 | 5 | 11 | 11 | 0 | 7 | 1 |
| bastar_forest_mining | MODIS_NRT | 2026-05-01 | 5 | 15 | 15 | 0 | 8 | 0 |

Bounds (west, south, east, north): Jamnagar coastal/refinery [69.7, 22.1, 70.5, 22.7]; Bastar forest/mining [80.5, 18.5, 82.0, 19.8]; Punjab agricultural plains [74.5, 30.3, 76.2, 31.7]. Region names indicate sampling contexts only, not verified land-use classes or event causes. Unreviewed event merges reduced the net event addition to 264; no reviewed ID was removed.

Five new candidates across source combinations received bounded enrichment: 5 OSM requests (3 available, 2 unavailable), 5 Copernicus requests (5 available). Remaining unavailable context stays null/unavailable; no values are fabricated. Acquisition and enrichment never approve reviews or invoke training.

## 6–8. Classes, sensors and reviewed class × sensor matrix

Counts below retain the original human review claims. All are currently V2-ineligible; model predictions in the application are not human labels.

| Reviewed class | S-NPP | NOAA-20 | NOAA-21 | MODIS |
|---|---:|---:|---:|---:|
| industrial_fire | 6 | 0 | 0 | 0 |
| persistent_industrial_thermal_source | 6 | 0 | 0 | 0 |
| agricultural_vegetation_fire | 7 | 0 | 0 | 0 |
| natural_thermal_event | 5 | 0 | 0 | 0 |
| possible_false_positive | 9 | 0 | 0 | 0 |

Raw satellite counts: {'N': 477, 'N20': 72, 'N21': 37, 'Aqua': 64, 'Terra': 1}. Instrument counts: {'VIIRS': 586, 'MODIS': 65}.

| Stored sensor combination | Events |
|---|---:|
| SNPP | 179 |
| NOAA20 | 54 |
| NOAA20 + NOAA21 + SNPP | 3 |
| MODIS | 26 |
| MODIS + SNPP | 8 |
| NOAA20 + SNPP | 1 |
| NOAA20 + NOAA21 | 1 |
| NOAA21 | 25 |

Reviewed sensor combinations: {'SNPP': 33}. Claimed split groups: 13; strict V2 eligible groups: 0.
Sampling-region detection counts: {'unrecorded': 52, 'korba': 2, 'angul_talcher': 61, 'chandrapur': 4, 'punjab_plains': 2, 'jamnagar_coastal_refinery': 18, 'bastar_forest_mining': 426, 'punjab_agricultural_plains': 86}.

## 9. Missing-feature profile

Entries are **missing events / event memberships**. Source/sensor groups overlap. A measurement is available when at least one contributing observation supplies it; full per-observation fields remain in evidence packets. Sensor-specific nulls are expected when an instrument is absent. Zero recurrence is a measured cohort result, not a missing value; it does not establish a complete historical baseline.

| All real events: field | Missing / 297 |
|---|---:|
| frp | 0 / 297 |
| primary_thermal | 0 / 297 |
| secondary_thermal | 0 / 297 |
| ndvi | 270 / 297 |
| osm_context | 261 / 297 |
| historical_recurrence | 0 / 297 |
| viirs_snpp_count | 0 / 297 |
| viirs_noaa20_count | 0 / 297 |
| viirs_noaa21_count | 0 / 297 |
| modis_count | 0 / 297 |
| independent_detection_count | 0 / 297 |
| nrt_sp_representation_count | 0 / 297 |
| unique_instrument_count | 0 / 297 |
| viirs_frp_mean | 26 / 297 |
| viirs_frp_max | 26 / 297 |
| modis_frp_mean | 263 / 297 |
| modis_frp_max | 263 / 297 |
| day_detection_fraction | 0 / 297 |
| night_detection_fraction | 0 / 297 |
| cross_sensor_confirmed | 0 / 297 |
| viirs_primary_thermal_mean | 26 / 297 |
| viirs_secondary_thermal_mean | 26 / 297 |
| modis_primary_thermal_mean | 263 / 297 |
| modis_secondary_thermal_mean | 263 / 297 |

### By sensor

| Field | SNPP | NOAA20 | NOAA21 | MODIS |
|---|---:|---:|---:|---:|
| frp | 0 / 191 | 0 / 59 | 0 / 29 | 0 / 34 |
| primary_thermal | 0 / 191 | 0 / 59 | 0 / 29 | 0 / 34 |
| secondary_thermal | 0 / 191 | 0 / 59 | 0 / 29 | 0 / 34 |
| ndvi | 168 / 191 | 57 / 59 | 28 / 29 | 31 / 34 |
| osm_context | 157 / 191 | 58 / 59 | 28 / 29 | 32 / 34 |
| historical_recurrence | 0 / 191 | 0 / 59 | 0 / 29 | 0 / 34 |
| viirs_snpp_count | 0 / 191 | 0 / 59 | 0 / 29 | 0 / 34 |
| viirs_noaa20_count | 0 / 191 | 0 / 59 | 0 / 29 | 0 / 34 |
| viirs_noaa21_count | 0 / 191 | 0 / 59 | 0 / 29 | 0 / 34 |
| modis_count | 0 / 191 | 0 / 59 | 0 / 29 | 0 / 34 |
| independent_detection_count | 0 / 191 | 0 / 59 | 0 / 29 | 0 / 34 |
| nrt_sp_representation_count | 0 / 191 | 0 / 59 | 0 / 29 | 0 / 34 |
| unique_instrument_count | 0 / 191 | 0 / 59 | 0 / 29 | 0 / 34 |
| viirs_frp_mean | 0 / 191 | 0 / 59 | 0 / 29 | 26 / 34 |
| viirs_frp_max | 0 / 191 | 0 / 59 | 0 / 29 | 26 / 34 |
| modis_frp_mean | 183 / 191 | 59 / 59 | 29 / 29 | 0 / 34 |
| modis_frp_max | 183 / 191 | 59 / 59 | 29 / 29 | 0 / 34 |
| day_detection_fraction | 0 / 191 | 0 / 59 | 0 / 29 | 0 / 34 |
| night_detection_fraction | 0 / 191 | 0 / 59 | 0 / 29 | 0 / 34 |
| cross_sensor_confirmed | 0 / 191 | 0 / 59 | 0 / 29 | 0 / 34 |
| viirs_primary_thermal_mean | 0 / 191 | 0 / 59 | 0 / 29 | 26 / 34 |
| viirs_secondary_thermal_mean | 0 / 191 | 0 / 59 | 0 / 29 | 26 / 34 |
| modis_primary_thermal_mean | 183 / 191 | 59 / 59 | 29 / 29 | 0 / 34 |
| modis_secondary_thermal_mean | 183 / 191 | 59 / 59 | 29 / 29 | 0 / 34 |

### By source

| Field | VIIRS_SNPP_NRT | VIIRS_NOAA20_NRT | VIIRS_NOAA21_NRT | MODIS_NRT | VIIRS_SNPP_SP | VIIRS_NOAA20_SP | MODIS_SP | unknown_legacy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| frp | 0 / 43 | 0 / 33 | 0 / 29 | 0 / 10 | 0 / 148 | 0 / 26 | 0 / 24 | N/A (0 events) |
| primary_thermal | 0 / 43 | 0 / 33 | 0 / 29 | 0 / 10 | 0 / 148 | 0 / 26 | 0 / 24 | N/A (0 events) |
| secondary_thermal | 0 / 43 | 0 / 33 | 0 / 29 | 0 / 10 | 0 / 148 | 0 / 26 | 0 / 24 | N/A (0 events) |
| ndvi | 21 / 43 | 31 / 33 | 28 / 29 | 9 / 10 | 147 / 148 | 26 / 26 | 22 / 24 | N/A (0 events) |
| osm_context | 10 / 43 | 32 / 33 | 28 / 29 | 9 / 10 | 147 / 148 | 26 / 26 | 23 / 24 | N/A (0 events) |
| historical_recurrence | 0 / 43 | 0 / 33 | 0 / 29 | 0 / 10 | 0 / 148 | 0 / 26 | 0 / 24 | N/A (0 events) |
| viirs_snpp_count | 0 / 43 | 0 / 33 | 0 / 29 | 0 / 10 | 0 / 148 | 0 / 26 | 0 / 24 | N/A (0 events) |
| viirs_noaa20_count | 0 / 43 | 0 / 33 | 0 / 29 | 0 / 10 | 0 / 148 | 0 / 26 | 0 / 24 | N/A (0 events) |
| viirs_noaa21_count | 0 / 43 | 0 / 33 | 0 / 29 | 0 / 10 | 0 / 148 | 0 / 26 | 0 / 24 | N/A (0 events) |
| modis_count | 0 / 43 | 0 / 33 | 0 / 29 | 0 / 10 | 0 / 148 | 0 / 26 | 0 / 24 | N/A (0 events) |
| independent_detection_count | 0 / 43 | 0 / 33 | 0 / 29 | 0 / 10 | 0 / 148 | 0 / 26 | 0 / 24 | N/A (0 events) |
| nrt_sp_representation_count | 0 / 43 | 0 / 33 | 0 / 29 | 0 / 10 | 0 / 148 | 0 / 26 | 0 / 24 | N/A (0 events) |
| unique_instrument_count | 0 / 43 | 0 / 33 | 0 / 29 | 0 / 10 | 0 / 148 | 0 / 26 | 0 / 24 | N/A (0 events) |
| viirs_frp_mean | 0 / 43 | 0 / 33 | 0 / 29 | 10 / 10 | 0 / 148 | 0 / 26 | 16 / 24 | N/A (0 events) |
| viirs_frp_max | 0 / 43 | 0 / 33 | 0 / 29 | 10 / 10 | 0 / 148 | 0 / 26 | 16 / 24 | N/A (0 events) |
| modis_frp_mean | 43 / 43 | 33 / 33 | 29 / 29 | 0 / 10 | 140 / 148 | 26 / 26 | 0 / 24 | N/A (0 events) |
| modis_frp_max | 43 / 43 | 33 / 33 | 29 / 29 | 0 / 10 | 140 / 148 | 26 / 26 | 0 / 24 | N/A (0 events) |
| day_detection_fraction | 0 / 43 | 0 / 33 | 0 / 29 | 0 / 10 | 0 / 148 | 0 / 26 | 0 / 24 | N/A (0 events) |
| night_detection_fraction | 0 / 43 | 0 / 33 | 0 / 29 | 0 / 10 | 0 / 148 | 0 / 26 | 0 / 24 | N/A (0 events) |
| cross_sensor_confirmed | 0 / 43 | 0 / 33 | 0 / 29 | 0 / 10 | 0 / 148 | 0 / 26 | 0 / 24 | N/A (0 events) |
| viirs_primary_thermal_mean | 0 / 43 | 0 / 33 | 0 / 29 | 10 / 10 | 0 / 148 | 0 / 26 | 16 / 24 | N/A (0 events) |
| viirs_secondary_thermal_mean | 0 / 43 | 0 / 33 | 0 / 29 | 10 / 10 | 0 / 148 | 0 / 26 | 16 / 24 | N/A (0 events) |
| modis_primary_thermal_mean | 43 / 43 | 33 / 33 | 29 / 29 | 0 / 10 | 140 / 148 | 26 / 26 | 0 / 24 | N/A (0 events) |
| modis_secondary_thermal_mean | 43 / 43 | 33 / 33 | 29 / 29 | 0 / 10 | 140 / 148 | 26 / 26 | 0 / 24 | N/A (0 events) |

### By claimed reviewed class

| Field | industrial_fire | persistent_industrial_thermal_source | agricultural_vegetation_fire | natural_thermal_event | possible_false_positive |
|---|---:|---:|---:|---:|---:|
| frp | 0 / 6 | 0 / 6 | 0 / 7 | 0 / 5 | 0 / 9 |
| primary_thermal | 0 / 6 | 0 / 6 | 0 / 7 | 0 / 5 | 0 / 9 |
| secondary_thermal | 0 / 6 | 0 / 6 | 0 / 7 | 0 / 5 | 0 / 9 |
| ndvi | 4 / 6 | 2 / 6 | 2 / 7 | 0 / 5 | 3 / 9 |
| osm_context | 0 / 6 | 0 / 6 | 0 / 7 | 0 / 5 | 0 / 9 |
| historical_recurrence | 0 / 6 | 0 / 6 | 0 / 7 | 0 / 5 | 0 / 9 |
| viirs_snpp_count | 0 / 6 | 0 / 6 | 0 / 7 | 0 / 5 | 0 / 9 |
| viirs_noaa20_count | 0 / 6 | 0 / 6 | 0 / 7 | 0 / 5 | 0 / 9 |
| viirs_noaa21_count | 0 / 6 | 0 / 6 | 0 / 7 | 0 / 5 | 0 / 9 |
| modis_count | 0 / 6 | 0 / 6 | 0 / 7 | 0 / 5 | 0 / 9 |
| independent_detection_count | 0 / 6 | 0 / 6 | 0 / 7 | 0 / 5 | 0 / 9 |
| nrt_sp_representation_count | 0 / 6 | 0 / 6 | 0 / 7 | 0 / 5 | 0 / 9 |
| unique_instrument_count | 0 / 6 | 0 / 6 | 0 / 7 | 0 / 5 | 0 / 9 |
| viirs_frp_mean | 0 / 6 | 0 / 6 | 0 / 7 | 0 / 5 | 0 / 9 |
| viirs_frp_max | 0 / 6 | 0 / 6 | 0 / 7 | 0 / 5 | 0 / 9 |
| modis_frp_mean | 6 / 6 | 6 / 6 | 7 / 7 | 5 / 5 | 9 / 9 |
| modis_frp_max | 6 / 6 | 6 / 6 | 7 / 7 | 5 / 5 | 9 / 9 |
| day_detection_fraction | 0 / 6 | 0 / 6 | 0 / 7 | 0 / 5 | 0 / 9 |
| night_detection_fraction | 0 / 6 | 0 / 6 | 0 / 7 | 0 / 5 | 0 / 9 |
| cross_sensor_confirmed | 0 / 6 | 0 / 6 | 0 / 7 | 0 / 5 | 0 / 9 |
| viirs_primary_thermal_mean | 0 / 6 | 0 / 6 | 0 / 7 | 0 / 5 | 0 / 9 |
| viirs_secondary_thermal_mean | 0 / 6 | 0 / 6 | 0 / 7 | 0 / 5 | 0 / 9 |
| modis_primary_thermal_mean | 6 / 6 | 6 / 6 | 7 / 7 | 5 / 5 | 9 / 9 |
| modis_secondary_thermal_mean | 6 / 6 | 6 / 6 | 7 / 7 | 5 / 5 | 9 / 9 |

## 10–12. Cross-sensor evidence, quality and readiness

**14 stored cross-sensor events; 0 reviewed cross-sensor events.** Confirmation means distinct known satellite/instrument combinations in one spatiotemporal cluster, including Aqua versus Terra. Thirteen events mix sensor families; one MODIS-only event combines platforms. It does not confirm a fire cause. NRT/SP equivalents use coordinate/time/platform identity with platform aliases normalized and contribute only once to independent summaries; both raw representations remain stored.

Quality checks: no duplicate candidate IDs, no exact duplicate provider observations, no conflicting labels across canonical files, no missing provenance, no invalid coordinates/FRP/confidence/timestamps, no missing detection references, and no exact NRT/SP duplicate representations detected. Different NRT/SP geolocation revisions can evade exact identity; no fuzzy scientific reconciliation was guessed.

**58 nearby-site pairs have different reviewed split groups within 5 km.** This is a conservative leakage warning, not 58 proven duplicate facilities. Exact overpass split conflicts: 0. Keep each physical facility, recurring source and equivalent overpass in one future split cohort after human reconciliation. No training split was created.

**33 reviews lack timestamps; 23 also have pre-existing evidence drift.** These issues were detected before acquisition. Explicit `freeze_reviewed` mode preserves existing reviewed event payloads and CSV cells and refuses any new cluster touching their detections. It does not make stale evidence eligible. The default acquisition guard remains strict. Source metadata appended to the canonical reviewed export is observed evidence only; no review date was backfilled.

**MODEL_V2_READY = false**, for these reasons:

- 100 additional timestamped, current-evidence reviewed events needed for Stage A
- At least 30 eligible reviewed events per class needed for serious V2 evaluation
- Fewer than 10 eligible independent split groups
- Eligible reviews do not cover multiple sensor families
- No eligible reviewed cross-sensor event
- Geographic/overpass split leakage risks require human reconciliation

Targets remain Stage A ≥100, Stage B ≥200, Stage C 300–500 genuinely reviewed events; ≥30 per class before serious evaluation, preferably ≥50. These are planning targets rather than evidence of scientific validity. The 297 candidates do not satisfy reviewed targets. The old V1 gate remains separate for compatibility.

## 13–14. Regression tests and validation

Added 19 test cases over the 175-test baseline (194 total): actual ingestion/counts for seven sources, independent NRT/SP evidence, satellite aliases, evidence-based legacy resolution and ambiguity, applied reconciliation preserving identity, event-level canonical metadata extension, timestamp rejection, class/sensor distribution, missingness, geographic leakage, V2 readiness, frozen-review overlap rollback, safe enrichment, and model artifact/no-train safeguards. Provider tests use mocks only.

| Command | Result |
|---|---|
| `PYTHONPATH=backend ./.venv/bin/pytest backend/tests -q` | 194 passed; two existing Starlette deprecation warnings |
| `node --test frontend/tests/api.test.mjs` | 12 passed |
| `npm --prefix frontend run typecheck` | Passed |
| `npm --prefix frontend run build` | Passed, Next.js 15.5.25 production build |
| `python3 -m py_compile backend/app/*.py` | Passed |
| `./.venv/bin/python -m py_compile backend/app/*.py backend/*review*.py backend/acquire_review_candidates.py` | Passed |
| `./.venv/bin/python -m pip check` | No broken requirements |
| `python3 -m pip check` | System interpreter fails: missing certifi, rpds-py, cffi dependencies; project venv is healthy |
| `git -c core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol diff --check` | Passed; standard CSV CRLF accepted |
| Frontend lint | No separate lint script exists; build ran its built-in checks |

Model V1 metadata and classifier SHA-256 match the pre-task snapshot. All original event rows, alerts, reviewed CSV cells, and raw observations were compared and preserved. Only legacy provenance metadata was intentionally added to original detection records.

## 15. Files and workflow

Core changes: `backend/app/intelligence.py`, `backend/app/main.py`, `backend/app/ml.py`, `backend/acquire_review_candidates.py`, `backend/export_review_candidates.py`, `backend/export_review_packets.py`, `backend/review_progress.py`, `backend/review_common.py`, `backend/prepare_review_row.py`, `backend/finalize_reviewed_labels.py`; regression tests in the existing FIRMS/acquisition/review/system test files.

UI: `frontend/components/MapView.tsx`, `frontend/app/page.tsx`, `frontend/lib/api.ts` add raw-observation pagination, a mode selector and sensor evidence without redesigning the dashboard. Raw mode shows source, satellite, instrument, acquisition time and FRP; its colors represent instruments, while event mode colors represent risk.

Canonical data reused: `data/review_candidates.csv`, `data/reviewed_labels.csv`, `data/review_acquisition_plan.json`, `data/review_acquisition_last_run.json`, existing `data/review_packets/` and safety-backup workflow. Database remains the root `thermaguard.db`. The last-run log describes the last plan; the complete three-plan acquisition table is preserved above. No duplicate training export was created.

Read-only audit: `PYTHONPATH=backend ./.venv/bin/python backend/review_progress.py --v2`. Legacy dry-run: `--reconcile-sources`; use `--apply` only for an intentional write under a single writer. Collection: `backend/acquire_review_candidates.py --plan data/review_acquisition_plan.json`; context-only bounded follow-up: `--enrich-unreviewed`. Run from the repository root with the API paused for CLI writes.

## 16. Working-tree diff

The working tree already contained earlier authorized reliability, source-support and cleanup changes. The following stat covers the whole current tracked diff, not just this acquisition task; untracked evidence packets/tests are additional. No commit or push was performed.

```text
 .gitignore                                  |   3 +
 README.md                                   |  88 +++-
 backend/.env.example                        |  18 +-
 backend/acquire_review_candidates.py        | 118 ++++-
 backend/app/config.py                       |  51 +-
 backend/app/database.py                     |  29 +-
 backend/app/intelligence.py                 | 142 ++++-
 backend/app/main.py                         | 778 +++++++++++++---------------
 backend/app/ml.py                           |  40 +-
 backend/app/providers.py                    | 336 +++++-------
 backend/app/review_validation.py            |  16 -
 backend/export_review_candidates.py         |   7 +-
 backend/export_review_packets.py            |   3 +-
 backend/finalize_reviewed_labels.py         |  40 +-
 backend/prepare_review_row.py               |   9 +-
 backend/review_common.py                    |  10 +-
 backend/review_progress.py                  | 216 +++++++-
 backend/tests/test_candidate_acquisition.py |  39 +-
 backend/tests/test_review_workflow.py       |   9 +-
 backend/tests/test_system.py                |  55 +-
 data/review_acquisition_last_run.json       | 441 ++++------------
 data/review_acquisition_plan.json           | 237 ++-------
 data/review_candidates.csv                  | 440 ++++++++++++++--
 data/review_packets/index.json              | 406 +++++++++++++--
 data/reviewed_labels.csv                    |  68 +--
 docs/ARCHITECTURE.md                        |  81 ++-
 docs/CLEANUP_MANIFEST.md                    | 129 +++++
 docs/DATA.md                                |  22 -
 docs/MODEL.md                               |  69 +++
 docs/REVIEW_ACQUISITION_REPORT.md           | 518 +++++++++++++++++-
 frontend/.env.example                       |   4 +-
 frontend/app/page.tsx                       |  24 +-
 frontend/components/MapView.tsx             |   4 +-
 frontend/lib/api.ts                         |  13 +-
 frontend/tests/api.test.mjs                 |   8 +-
 review_next_5.shTAB                         | 107 ----
 36 files changed, 3057 insertions(+), 1521 deletions(-)
```

## 17. Remaining scientific limitations

- Human review is the bottleneck: all 264 new candidates need independent evidence and exactly one approved class. Existing 33 claims need real timestamped re-review; 23 require evidence reconciliation. Do not infer class from a sampling region, V1 prediction, OSM, Ollama, FRP or confidence.
- S-NPP SP and Bastar dominate observations. The dataset is neither class-balanced nor geographically representative. Natural-event and false-positive classes cannot be guaranteed by sampling alone.
- MODIS and VIIRS differ in spatial resolution, bands, sensitivity, observation time and processing. Preserve per-instrument thermal/FRP fields; missingness can encode sensor identity and bias a model. FRP shares MW units but is not automatically sensor-harmonized.
- 270/297 events lack NDVI and 261/297 lack available OSM context. Limited enrichment succeeded only for a bounded subset. Image timing/cloud masks and context accuracy require review.
- Cross-sensor spatial/temporal clustering is supporting evidence, not proof of one physical cause. Existing fixed thresholds can merge neighboring activities or fragment recurring sites. Exact NRT/SP matching does not resolve shifted geolocation or reprocessing.
- The 58 geographic split warnings require facility/cohort review before future evaluation. No new train/test split or Model V2 artifact exists.
- The in-process ingestion lock does not coordinate separate processes; CLI writes require the API to be paused. Filesystem review edits must not run concurrently with acquisition/enrichment. System Python dependency warnings remain separate from the validated project environment.

---

## Earlier acquisition record (historical; superseded by the audit above)

# ThermaGuard AI — real candidate expansion report

Verified September 11, 2026. Expanded the pool from **13 to 33 real events**, within
the requested 30–50 range. No labels or approvals were generated and no training occurred.

## Real data

- **69 new unique FIRMS observations** stored, giving **121 real detections** total.
- **102 validated observation rows returned** across two network-enabled passes;
  33 were repeat observations and were deduplicated. Zero validation rejections
  occurred in successfully returned responses.
- 30 network-enabled requests: 29 returned responses; one network failure was
  retried successfully in the second pass. A separate initial sandbox attempt
  made 12 failed requests and stored nothing.
- **20 new events**, zero removed/reidentified events, **33 candidates** total.
- All acquisitions used **VIIRS_SNPP_NRT**, stored satellite `N` / instrument `VIIRS`.
- New periods: **August 10, September 5 and September 8, 2026**. Combined candidate
  dates: **August 5–September 10, 2026** (UTC).
- **Zero alerts created** during acquisition. Existing successful OSM/Copernicus
  context was preserved. New historical events have explicit unavailable context;
  no enrichment or incident details were fabricated.

| Queried region | Requests | Returned rows | New detections | New events |
|---|---:|---:|---:|---:|
| jamnagar | 5 | 0 | 0 | 0 |
| korba | 5 | 4 | 2 | 2 |
| angul_talcher | 5 | 87 | 61 | 12 |
| chandrapur | 5 | 8 | 4 | 4 |
| punjab_plains | 5 | 3 | 2 | 2 |
| central_madhya_pradesh | 5 | 0 | 0 | 0 |

Returned-row totals exclude the unmeasurable failed response; they do not assert
that response contained zero observations. Jamnagar and central Madhya Pradesh
returned no detections in the successful queried windows. The second pass exhausted
the plan at 33 candidates; its internal target of 40 was not reached. Collection
stopped within the user's requested range.

Current representation: Hazira **11**, Angul–Talcher **12**, Chandrapur **4**,
Korba **2**, Punjab plains **2**, plus **2 existing Gujarat events outside the
configured search-zone map**. Five named search zones are represented. These zone
counts do not establish five independent scientific training groups.

## Human review and model

| Measure | Verified value |
|---|---:|
| Reviewed candidates | 1 |
| Eligible reviewed candidates | 1 |
| Unreviewed candidates | 32 |
| Classes represented | 1 / 5 |
| Human split groups | 1 / 10 |
| Training ready | false |
| Model available | false |
| Training performed | **No** |

Eligible class counts: `persistent_industrial_thermal_source = 1`;
`industrial_fire = 0`; `agricultural_vegetation_fire = 0`;
`natural_thermal_event = 0`; `possible_false_positive = 0`.

The published training dataset remains absent; `ml.status()` therefore reports
zero published eligible rows, while the candidate validator reports one eligible
candidate. These are different inputs. The gate remains 30 eligible human-reviewed
non-demo events, all five classes, and ten genuinely independent split groups.

The complete candidate row for **TG-firms-12a727a697efdb9146a2** was compared to the
pre-acquisition backup and is **exactly unchanged**, including its human fields and
any custom columns. The full stored event payload passed the transaction guard
throughout acquisition. Its group remains `hazira_sep_2026`. **No event-ID
reconciliation or label transfer was needed.**

## Files created

- `backend/acquire_review_candidates.py`: plan parsing, real-only ingestion,
  bounded provider requests, review backups, transactional evidence guard, no alerts.
- `backend/candidate_inventory.py`: read-only geographic/date inventory and cohort suggestions.
- `backend/review_queue.py`: chronological filtering without predicted-class ranking.
- `backend/export_review_packets.py`: neutral stored-evidence packets and unverified search aids.
- `backend/app/ml.py`: shared source-reference syntax guard.
- `backend/tests/test_candidate_acquisition.py`: 43 additional isolated test cases.
- `data/review_acquisition_plan.example.json` and `data/review_acquisition_plan.json`.
- `data/review_packets/`: **32 Markdown packets**, plus `index.json`.
- `data/review_acquisition_last_run.json`, archived pass reports, byte-for-byte CSV
  backups and reviewed-row snapshots under `data/backups/`.
- `docs/REVIEW_ACQUISITION.md` and this report.

## Files modified in this task

- `backend/app/main.py`: optional deferred commit for transaction-safe pipeline reuse.
- `backend/app/ml.py`: stronger reference and metadata eligibility checks; unchanged feature list/gate.
- `backend/review_common.py`: shared source-reference guard for explicit approval/publication.
- `backend/export_review_candidates.py`: refuse disappearance of reviewed event IDs.
- `backend/tests/test_system.py` and `backend/tests/test_review_workflow.py`: replace
  obsolete placeholder success fixtures with example-domain test references;
  retain unreviewed removal coverage and add reviewed-removal refusal coverage.
- `data/review_candidates.csv`: real new candidates; existing reviewed row preserved.
- `README.md`, `docs/ARCHITECTURE.md`, `docs/MODEL.md`: acquisition and grouping documentation.
- Configured SQLite database: 69 new real detections and 20 new real events.

Other pre-existing repository modifications were retained. No `.env`, model
artifact, or published reviewed-label file was changed.

## Verification

**115 tests passed**, with two existing Starlette dependency deprecation warnings.
Tests ran successfully before any real acquisition and again after final changes.
Coverage includes plan/date/bounds validation, raw-provenance checking, real-only
operation, deduplication, alert suppression, rollback for reviewed ID/evidence
changes, exact manual/custom-note preservation, exporter idempotency, source
placeholder rejection, packet neutrality, inventory/queue/cohort behavior, no
review-only feature leakage, and the unchanged training gate. No classifier was trained.

The exporter, inventory, progress report, validator, queue and packet exporter were
run on the resulting real data. Final CSV export was a byte-identical no-op. The
validator exited 1 because training readiness is false; it reported no data
validation problems. The packet manifest lists exactly 32 current unreviewed files.

## Inspect the next five events

These exact commands display evidence without changing review fields:

```sh
cd /Users/chandankumarmahato/Desktop/SIH2026
PYTHONPATH=backend ./.venv/bin/python backend/review_queue.py --limit 5

for event_id in \
  TG-firms-17a1d9abb72d51592396 \
  TG-firms-4ee5757a7f0de593d158 \
  TG-firms-2cccb1d15213eca9a6c1 \
  TG-firms-889ac864d33ccc099b73 \
  TG-firms-b21337d75f2e1696a2f7
do
  PYTHONPATH=backend ./.venv/bin/python backend/prepare_review_row.py "$event_id"
done
```

For each event, verify the corresponding packet and independent sources before
using explicit approval flags. The command above does not select a label, create a
reference, or mark anything reviewed. Full approval and grouping guidance is in
[REVIEW_ACQUISITION.md](REVIEW_ACQUISITION.md).
