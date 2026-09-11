# Review evidence: TG-firms-3397d3c737eba55ac004

```text
THERMAGUARD — HUMAN REVIEW EVIDENCE
Stored evidence only. No class is suggested; the final label belongs to the reviewer.

Identity and observation aggregates (FRP: MW; brightness: K; duration: hours)
  event_id: TG-firms-3397d3c737eba55ac004
  is_demo: No
  latitude: 22.92957
  longitude: 70.10769
  start_time: 2026-09-10T08:26:00+00:00
  last_seen_time: 2026-09-10T08:26:00+00:00
  detection_count: 1
  mean_frp: 7.09
  max_frp: 7.09
  mean_brightness: 338.96
  max_brightness: 338.96
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
  osm_context_available: Yes
  distance_to_industrial_m: 0.0
  distance_to_refinery_m: Unavailable
  distance_to_powerplant_m: Unavailable
  distance_to_factory_m: Unavailable
  distance_to_forest_m: Unavailable
  distance_to_farmland_m: Unavailable
  distance_to_residential_m: Unavailable
  nearby_industrial_count: 1
  nearby_facility_count: 1
  landuse_class: industrial
  nearby_facility_names: Tuna-Tekra Container Terminal

Satellite context (check acquisition time against event time)
  satellite_context_available: No
  ndvi: Unavailable
  acquisition_date: Unavailable
  land_cover: Unavailable

Decision-support risk — not classification confidence
  risk_score: 13
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
    "firms-3397d3c737eba55ac004"
  ],
  "source_sensors": [
    "NASA FIRMS / N / VIIRS"
  ],
  "provider_queries": [],
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
    "distance_to_industrial_m": 0.0,
    "distance_to_refinery_m": null,
    "distance_to_powerplant_m": null,
    "distance_to_factory_m": null,
    "distance_to_forest_m": null,
    "distance_to_farmland_m": null,
    "distance_to_residential_m": null,
    "osm_context_available": true,
    "source": "OpenStreetMap Overpass",
    "retrieved_at": "2026-09-10T21:27:41.206435+00:00",
    "search_radius_m": 5000,
    "landuse_class": "industrial",
    "nearby_facility_count": 1,
    "nearby_industrial_count": 1,
    "facilities": [
      {
        "osm_id": "way/361301736",
        "name": "Tuna-Tekra Container Terminal",
        "categories": [
          "industrial"
        ],
        "distance_m": 0.0,
        "geometry_reference": "https://www.openstreetmap.org/way/361301736"
      }
    ],
    "coverage_note": "Missing tags or matches do not establish absence; distances limited to query area.",
    "satellite_context_available": false,
    "ndvi": null,
    "land_cover": null,
    "vegetation_fraction": null,
    "built_up_fraction": null,
    "satellite_image_reference": null,
    "provider": "copernicus",
    "reason": "no_sentinel2_observation_available"
  }
}
```

## Potential evidence to verify manually

These links and search terms are search aids, NOT verified incident evidence. A reviewer must inspect relevance, date, location, and source reliability.

- Coordinates: 22.929570, 70.107690
- [NASA FIRMS map](https://firms.modaps.eosdis.nasa.gov/map/#d:2026-09-10..2026-09-10;@70.10769,22.92957,12z)
- [OpenStreetMap location](https://www.openstreetmap.org/?mlat=22.92957&mlon=70.10769#map=14/22.92957/70.10769)
- [External incident/news search](https://www.google.com/search?q=22.9296+70.1077+fire+2026-09-10)
- Search terms: `22.9296 70.1077 fire 2026-09-10`; optionally add a stored nearby facility name.
