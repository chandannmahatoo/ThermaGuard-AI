# Review evidence: TG-firms-889ac864d33ccc099b73

```text
THERMAGUARD — HUMAN REVIEW EVIDENCE
Stored evidence only. No class is suggested; the final label belongs to the reviewer.

Identity and observation aggregates (FRP: MW; brightness: K; duration: hours)
  event_id: TG-firms-889ac864d33ccc099b73
  is_demo: No
  latitude: 19.96435
  longitude: 79.33541
  start_time: 2026-08-10T20:34:00+00:00
  last_seen_time: 2026-08-10T20:34:00+00:00
  detection_count: 1
  mean_frp: 1.08
  max_frp: 1.08
  mean_brightness: 308.94
  max_brightness: 308.94
  persistence_days: 1
  duration_hours: 0.0
  night_fraction: 1.0

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
  risk_score: 0
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
    "firms-889ac864d33ccc099b73"
  ],
  "source_sensors": [
    "NASA FIRMS / N / VIIRS"
  ],
  "provider_queries": [
    {
      "region": "chandrapur",
      "source": "VIIRS_SNPP_NRT",
      "bounds": [
        79.0,
        19.6,
        79.7,
        20.3
      ],
      "start_date": "2026-08-10",
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

- Coordinates: 19.964350, 79.335410
- [NASA FIRMS map](https://firms.modaps.eosdis.nasa.gov/map/#d:2026-08-10..2026-08-10;@79.33541,19.96435,12z)
- [OpenStreetMap location](https://www.openstreetmap.org/?mlat=19.96435&mlon=79.33541#map=14/19.96435/79.33541)
- [External incident/news search](https://www.google.com/search?q=19.9643+79.3354+fire+2026-08-10)
- Search terms: `19.9643 79.3354 fire 2026-08-10`; optionally add a stored nearby facility name.
