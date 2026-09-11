# Review evidence: TG-firms-4ee5757a7f0de593d158

```text
THERMAGUARD — HUMAN REVIEW EVIDENCE
Stored evidence only. No class is suggested; the final label belongs to the reviewer.

Identity and observation aggregates (FRP: MW; brightness: K; duration: hours)
  event_id: TG-firms-4ee5757a7f0de593d158
  is_demo: No
  latitude: 21.10539
  longitude: 72.6411275
  start_time: 2026-08-09T20:53:00+00:00
  last_seen_time: 2026-08-09T20:53:00+00:00
  detection_count: 8
  mean_frp: 2.095
  max_frp: 2.5
  mean_brightness: 314.5025
  max_brightness: 337.04
  persistence_days: 1
  duration_hours: 0.0
  night_fraction: 1.0

Derived historical context
  recurrence_count: 1
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
  distance_to_powerplant_m: 1326.4
  distance_to_factory_m: 0.0
  distance_to_forest_m: Unavailable
  distance_to_farmland_m: 3341.0
  distance_to_residential_m: 197.0
  nearby_industrial_count: 8
  nearby_facility_count: 13
  landuse_class: industrial
  nearby_facility_names: ArcelorMittal Nippon Steel India; Bhander Power Plant; Hazira II (Essar) Power Plant; Hazira Power Plant; L&T; Shell Energy India Private Limited

Satellite context (check acquisition time against event time)
  satellite_context_available: Yes
  ndvi: 0.1447
  acquisition_date: 2026-08-04
  land_cover: Unavailable

Decision-support risk — not classification confidence
  risk_score: 21
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
    "firms-4ee5757a7f0de593d158",
    "firms-8c932b7438b4a5699a8a",
    "firms-90fa39b11779a6f8d547",
    "firms-96bff07b35a25e7a386a",
    "firms-d7b9f020a17fceaa1776",
    "firms-d9620ede9b7bb919b643",
    "firms-dc89b1020f8d8863a2a0",
    "firms-f7745fa1ca784548209a"
  ],
  "source_sensors": [
    "NASA FIRMS / N / VIIRS"
  ],
  "provider_queries": [],
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
    "detection_frequency": 8.0,
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
    "osm_context_available": true,
    "osm_reason": null,
    "satellite_context_available": true,
    "ndvi": 0.1447,
    "land_cover": null,
    "vegetation_fraction": null,
    "built_up_fraction": null,
    "satellite_image_reference": "Sentinel-2 L2A via Copernicus Data Space Sentinel Hub Statistical API",
    "provider": "copernicus",
    "reason": null,
    "distance_to_industrial_m": 0.0,
    "distance_to_refinery_m": null,
    "distance_to_powerplant_m": 1326.4,
    "distance_to_factory_m": 0.0,
    "distance_to_forest_m": null,
    "distance_to_farmland_m": 3341.0,
    "distance_to_residential_m": 197.0,
    "source": "Copernicus Data Space Ecosystem",
    "osm_source": "OpenStreetMap Overpass",
    "retrieved_at": "2026-09-10T22:23:16.183421+00:00",
    "osm_retrieved_at": "2026-09-10T22:19:06.581718+00:00",
    "search_radius_m": 5000,
    "landuse_class": "industrial",
    "nearby_facility_count": 13,
    "nearby_industrial_count": 8,
    "facilities": [
      {
        "osm_id": "way/104647203",
        "name": "ArcelorMittal Nippon Steel India",
        "categories": [
          "industrial",
          "factory"
        ],
        "distance_m": 0.0,
        "geometry_reference": "https://www.openstreetmap.org/way/104647203"
      },
      {
        "osm_id": "way/104647207",
        "name": "L&T",
        "categories": [
          "industrial",
          "factory"
        ],
        "distance_m": 4523.9,
        "geometry_reference": "https://www.openstreetmap.org/way/104647207"
      },
      {
        "osm_id": "way/121765355",
        "name": "Shell Energy India Private Limited",
        "categories": [
          "industrial"
        ],
        "distance_m": 1819.9,
        "geometry_reference": "https://www.openstreetmap.org/way/121765355"
      },
      {
        "osm_id": "way/230025518",
        "name": null,
        "categories": [
          "farmland"
        ],
        "distance_m": 3341.0,
        "geometry_reference": "https://www.openstreetmap.org/way/230025518"
      },
      {
        "osm_id": "way/596668532",
        "name": null,
        "categories": [
          "residential"
        ],
        "distance_m": 2230.1,
        "geometry_reference": "https://www.openstreetmap.org/way/596668532"
      },
      {
        "osm_id": "way/596668543",
        "name": null,
        "categories": [
          "residential"
        ],
        "distance_m": 197.0,
        "geometry_reference": "https://www.openstreetmap.org/way/596668543"
      },
      {
        "osm_id": "way/637909310",
        "name": null,
        "categories": [
          "industrial"
        ],
        "distance_m": 1720.7,
        "geometry_reference": "https://www.openstreetmap.org/way/637909310"
      },
      {
        "osm_id": "way/799237879",
        "name": null,
        "categories": [
          "factory"
        ],
        "distance_m": 4559.6,
        "geometry_reference": "https://www.openstreetmap.org/way/799237879"
      },
      {
        "osm_id": "way/799237889",
        "name": null,
        "categories": [
          "factory"
        ],
        "distance_m": 4732.5,
        "geometry_reference": "https://www.openstreetmap.org/way/799237889"
      },
      {
        "osm_id": "way/823272713",
        "name": "Hazira Power Plant",
        "categories": [
          "industrial",
          "powerplant"
        ],
        "distance_m": 1326.4,
        "geometry_reference": "https://www.openstreetmap.org/way/823272713"
      },
      {
        "osm_id": "way/916863896",
        "name": "Hazira II (Essar) Power Plant",
        "categories": [
          "industrial",
          "powerplant"
        ],
        "distance_m": 1413.4,
        "geometry_reference": "https://www.openstreetmap.org/way/916863896"
      },
      {
        "osm_id": "way/1157017752",
        "name": "Bhander Power Plant",
        "categories": [
          "industrial",
          "powerplant"
        ],
        "distance_m": 1616.0,
        "geometry_reference": "https://www.openstreetmap.org/way/1157017752"
      },
      {
        "osm_id": "way/1187716203",
        "name": null,
        "categories": [
          "industrial"
        ],
        "distance_m": 2671.2,
        "geometry_reference": "https://www.openstreetmap.org/way/1187716203"
      }
    ],
    "coverage_note": "Missing tags or matches do not establish absence; distances limited to query area.",
    "acquisition_date": "2026-08-04",
    "satellite_source": "Copernicus Data Space Ecosystem",
    "satellite_retrieved_at": "2026-09-10T22:23:16.183421+00:00",
    "search_radius_note": "~2 km around event center",
    "observation_sample_count": 40000
  }
}
```

## Potential evidence to verify manually

These links and search terms are search aids, NOT verified incident evidence. A reviewer must inspect relevance, date, location, and source reliability.

- Coordinates: 21.105390, 72.641127
- [NASA FIRMS map](https://firms.modaps.eosdis.nasa.gov/map/#d:2026-08-09..2026-08-09;@72.6411275,21.10539,12z)
- [OpenStreetMap location](https://www.openstreetmap.org/?mlat=21.10539&mlon=72.6411275#map=14/21.10539/72.6411275)
- [External incident/news search](https://www.google.com/search?q=21.1054+72.6411+fire+2026-08-09)
- Search terms: `21.1054 72.6411 fire 2026-08-09`; optionally add a stored nearby facility name.
