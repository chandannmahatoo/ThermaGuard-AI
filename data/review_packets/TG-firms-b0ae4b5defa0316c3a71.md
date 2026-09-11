# Review evidence: TG-firms-b0ae4b5defa0316c3a71

```text
THERMAGUARD — HUMAN REVIEW EVIDENCE
Stored evidence only. No class is suggested; the final label belongs to the reviewer.

Identity and observation aggregates (FRP: MW; brightness: K; duration: hours)
  event_id: TG-firms-b0ae4b5defa0316c3a71
  is_demo: No
  latitude: 31.21099
  longitude: 75.96707
  start_time: 2026-09-08T07:24:00+00:00
  last_seen_time: 2026-09-08T07:24:00+00:00
  detection_count: 1
  mean_frp: 2.47
  max_frp: 2.47
  mean_brightness: 329.07
  max_brightness: 329.07
  persistence_days: 1
  duration_hours: 0.0
  night_fraction: 0.0

Derived historical context
  recurrence_count: 0
  historical_baseline_available: No
  historical_mean_frp: Unavailable

Historical abnormality — interpretation, not a class label
  abnormality_score: Unavailable
  abnormality_status: unavailable
  baseline_available: No

OSM context (distances: metres; missing tags do not establish absence)
  osm_context_available: No
  distance_to_industrial_m: Unavailable
  distance_to_refinery_m: Unavailable
  distance_to_powerplant_m: Unavailable
  distance_to_factory_m: Unavailable
  distance_to_forest_m: Unavailable
  distance_to_farmland_m: Unavailable
  distance_to_residential_m: Unavailable
  nearby_industrial_count: Unavailable
  nearby_facility_count: Unavailable
  landuse_class: Unavailable
  nearby_facility_names: Unavailable (no stored names)

Satellite context (check acquisition time against event time)
  satellite_context_available: No
  ndvi: Unavailable
  acquisition_date: Unavailable
  land_cover: Unavailable

Decision-support risk — not classification confidence
  risk_score: 1
  risk_level: Normal

Evidence checklist:
[ ] Industrial facility context checked
[ ] Historical persistence checked
[ ] Agricultural/vegetation context checked
[ ] Natural thermal explanation checked
[ ] Possible false-positive explanation checked
[ ] External source/reference collected
[ ] Final class selected by reviewer
No checklist completion or review approval has been recorded by this summary.
```

## Stored source and detailed context

```json
{
  "detection_ids": [
    "firms-b0ae4b5defa0316c3a71"
  ],
  "source_sensors": [
    "NASA FIRMS / N / VIIRS"
  ],
  "provider_queries": [
    {
      "region": "punjab_plains",
      "source": "VIIRS_SNPP_NRT",
      "bounds": [
        74.5,
        30.3,
        76.2,
        31.7
      ],
      "start_date": "2026-09-08",
      "days": 1
    }
  ],
  "history": {
    "historical_baseline_available": false,
    "historical_event_count": 0,
    "recurrence_count": 0,
    "historical_mean_frp": null,
    "historical_max_frp": null,
    "historical_std_frp": null,
    "historical_mean_brightness": null,
    "historical_mean_spread_km": null,
    "historical_mean_duration_hours": null,
    "historical_mean_frequency": null,
    "detection_frequency": 1.0,
    "time_of_day_pattern": "day_dominant",
    "history_window_days": 365,
    "history_radius_km": 5.0,
    "minimum_baseline_events": 5,
    "reason": "insufficient_history"
  },
  "abnormality": {
    "baseline_available": false,
    "abnormality_score": null,
    "abnormality_status": "unavailable",
    "reason": "insufficient_history",
    "explanation_features": {
      "frp_ratio": null,
      "brightness_ratio": null,
      "spatial_spread_ratio": null,
      "persistence_ratio": null,
      "frequency_ratio": null,
      "historical_event_count": 0
    },
    "historical_mean_frp": null
  },
  "osm_satellite_context": {
    "osm_context_available": false,
    "osm_reason": "historical_backfill_not_enriched",
    "satellite_context_available": false,
    "ndvi": null,
    "land_cover": null,
    "vegetation_fraction": null,
    "built_up_fraction": null,
    "satellite_image_reference": null,
    "provider": "copernicus",
    "reason": "historical_backfill_not_enriched"
  }
}
```

## Potential evidence to verify manually

These links and search terms are search aids, NOT verified incident evidence. A reviewer must inspect relevance, date, location, and source reliability.

- Coordinates: 31.210990, 75.967070
- [NASA FIRMS map](https://firms.modaps.eosdis.nasa.gov/map/#d:2026-09-08..2026-09-08;@75.96707,31.21099,12z)
- [OpenStreetMap location](https://www.openstreetmap.org/?mlat=31.21099&mlon=75.96707#map=14/31.21099/75.96707)
- [External incident/news search](https://www.google.com/search?q=31.2110+75.9671+fire+2026-09-08)
- Search terms: `31.2110 75.9671 fire 2026-09-08`; optionally add a stored nearby facility name.
