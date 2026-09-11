# Review evidence: TG-firms-fd17266b4d6fdaaa1026

```text
THERMAGUARD — HUMAN REVIEW EVIDENCE
Stored evidence only. No class is suggested; the final label belongs to the reviewer.

Identity and observation aggregates (FRP: MW; brightness: K; duration: hours)
  event_id: TG-firms-fd17266b4d6fdaaa1026
  is_demo: No
  latitude: 20.865318
  longitude: 84.990644
  start_time: 2026-09-05T08:18:00+00:00
  last_seen_time: 2026-09-05T20:46:00+00:00
  detection_count: 5
  mean_frp: 2.798
  max_frp: 6.34
  mean_brightness: 318.76
  max_brightness: 332.66
  persistence_days: 1
  duration_hours: 12.466666666666667
  night_fraction: 0.8

Derived historical context
  recurrence_count: 1
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
  risk_score: 8
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
    "firms-fd17266b4d6fdaaa1026",
    "firms-051b7dda16b58e2b096a",
    "firms-35c4cfa567078f56f26b",
    "firms-76e91310bab8df6d4946",
    "firms-b258fc1dae340e6f24e5"
  ],
  "source_sensors": [
    "NASA FIRMS / N / VIIRS"
  ],
  "provider_queries": [
    {
      "region": "angul_talcher",
      "source": "VIIRS_SNPP_NRT",
      "bounds": [
        84.8,
        20.7,
        85.5,
        21.3
      ],
      "start_date": "2026-09-05",
      "days": 1
    },
    {
      "region": "angul_talcher",
      "source": "VIIRS_SNPP_NRT",
      "bounds": [
        84.8,
        20.7,
        85.5,
        21.3
      ],
      "start_date": "2026-09-05",
      "days": 1
    },
    {
      "region": "angul_talcher",
      "source": "VIIRS_SNPP_NRT",
      "bounds": [
        84.8,
        20.7,
        85.5,
        21.3
      ],
      "start_date": "2026-09-05",
      "days": 1
    },
    {
      "region": "angul_talcher",
      "source": "VIIRS_SNPP_NRT",
      "bounds": [
        84.8,
        20.7,
        85.5,
        21.3
      ],
      "start_date": "2026-09-05",
      "days": 1
    },
    {
      "region": "angul_talcher",
      "source": "VIIRS_SNPP_NRT",
      "bounds": [
        84.8,
        20.7,
        85.5,
        21.3
      ],
      "start_date": "2026-09-05",
      "days": 1
    }
  ],
  "history": {
    "historical_baseline_available": false,
    "historical_event_count": 1,
    "recurrence_count": 1,
    "historical_mean_frp": null,
    "historical_max_frp": null,
    "historical_std_frp": null,
    "historical_mean_brightness": null,
    "historical_mean_spread_km": null,
    "historical_mean_duration_hours": null,
    "historical_mean_frequency": null,
    "detection_frequency": 0.40106951871657753,
    "time_of_day_pattern": "night_dominant",
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
      "historical_event_count": 1
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

- Coordinates: 20.865318, 84.990644
- [NASA FIRMS map](https://firms.modaps.eosdis.nasa.gov/map/#d:2026-09-05..2026-09-05;@84.990644,20.865318,12z)
- [OpenStreetMap location](https://www.openstreetmap.org/?mlat=20.865318&mlon=84.990644#map=14/20.865318/84.990644)
- [External incident/news search](https://www.google.com/search?q=20.8653+84.9906+fire+2026-09-05)
- Search terms: `20.8653 84.9906 fire 2026-09-05`; optionally add a stored nearby facility name.
