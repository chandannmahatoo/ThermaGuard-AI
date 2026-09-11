# Review evidence: TG-firms-d8592b532b1f032e87ac

```text
THERMAGUARD — HUMAN REVIEW EVIDENCE
Stored evidence only. No class is suggested; the final label belongs to the reviewer.

Identity and observation aggregates (FRP: MW; brightness: K; duration: hours)
  event_id: TG-firms-d8592b532b1f032e87ac
  is_demo: No
  latitude: 21.10456
  longitude: 72.645415
  start_time: 2026-08-17T20:02:00+00:00
  last_seen_time: 2026-08-17T20:02:00+00:00
  detection_count: 2
  mean_frp: 3.06
  max_frp: 3.43
  mean_brightness: 307.34000000000003
  max_brightness: 308.27
  persistence_days: 1
  duration_hours: 0.0
  night_fraction: 1.0

Derived historical context
  recurrence_count: 3
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
  distance_to_powerplant_m: 958.9
  distance_to_factory_m: 0.0
  distance_to_forest_m: Unavailable
  distance_to_farmland_m: 3544.0
  distance_to_residential_m: 182.1
  nearby_industrial_count: 8
  nearby_facility_count: 13
  landuse_class: industrial
  nearby_facility_names: ArcelorMittal Nippon Steel India; Bhander Power Plant; Hazira II (Essar) Power Plant; Hazira Power Plant; L&T; Shell Energy India Private Limited

Satellite context (check acquisition time against event time)
  satellite_context_available: No
  ndvi: Unavailable
  acquisition_date: Unavailable
  land_cover: Unavailable

Decision-support risk — not classification confidence
  risk_score: 26
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
    "firms-d8592b532b1f032e87ac",
    "firms-ddce9863942942a6285f"
  ],
  "source_sensors": [
    "NASA FIRMS / N / VIIRS"
  ],
  "provider_queries": [],
  "history": {
    "historical_baseline_available": false,
    "historical_event_count": 3,
    "recurrence_count": 3,
    "historical_mean_frp": null,
    "historical_max_frp": null,
    "historical_std_frp": null,
    "historical_mean_brightness": null,
    "historical_mean_spread_km": null,
    "historical_mean_duration_hours": null,
    "historical_mean_frequency": null,
    "detection_frequency": 2.0,
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
      "historical_event_count": 3
    },
    "historical_mean_frp": null
  },
  "osm_satellite_context": {
    "osm_context_available": true,
    "osm_reason": null,
    "satellite_context_available": false,
    "ndvi": null,
    "land_cover": null,
    "vegetation_fraction": null,
    "built_up_fraction": null,
    "satellite_image_reference": null,
    "provider": "copernicus",
    "reason": "no_sentinel2_observation_available",
    "distance_to_industrial_m": 0.0,
    "distance_to_refinery_m": null,
    "distance_to_powerplant_m": 958.9,
    "distance_to_factory_m": 0.0,
    "distance_to_forest_m": null,
    "distance_to_farmland_m": 3544.0,
    "distance_to_residential_m": 182.1,
    "source": "OpenStreetMap Overpass",
    "osm_source": "OpenStreetMap Overpass",
    "retrieved_at": "2026-09-10T22:19:15.957861+00:00",
    "osm_retrieved_at": "2026-09-10T22:19:15.957881+00:00",
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
        "distance_m": 4589.6,
        "geometry_reference": "https://www.openstreetmap.org/way/104647207"
      },
      {
        "osm_id": "way/121765355",
        "name": "Shell Energy India Private Limited",
        "categories": [
          "industrial"
        ],
        "distance_m": 2188.4,
        "geometry_reference": "https://www.openstreetmap.org/way/121765355"
      },
      {
        "osm_id": "way/230025518",
        "name": null,
        "categories": [
          "farmland"
        ],
        "distance_m": 3544.0,
        "geometry_reference": "https://www.openstreetmap.org/way/230025518"
      },
      {
        "osm_id": "way/596668532",
        "name": null,
        "categories": [
          "residential"
        ],
        "distance_m": 2230.6,
        "geometry_reference": "https://www.openstreetmap.org/way/596668532"
      },
      {
        "osm_id": "way/596668543",
        "name": null,
        "categories": [
          "residential"
        ],
        "distance_m": 182.1,
        "geometry_reference": "https://www.openstreetmap.org/way/596668543"
      },
      {
        "osm_id": "way/637909310",
        "name": null,
        "categories": [
          "industrial"
        ],
        "distance_m": 1632.2,
        "geometry_reference": "https://www.openstreetmap.org/way/637909310"
      },
      {
        "osm_id": "way/799237879",
        "name": null,
        "categories": [
          "factory"
        ],
        "distance_m": 4609.5,
        "geometry_reference": "https://www.openstreetmap.org/way/799237879"
      },
      {
        "osm_id": "way/799237889",
        "name": null,
        "categories": [
          "factory"
        ],
        "distance_m": 4728.1,
        "geometry_reference": "https://www.openstreetmap.org/way/799237889"
      },
      {
        "osm_id": "way/823272713",
        "name": "Hazira Power Plant",
        "categories": [
          "industrial",
          "powerplant"
        ],
        "distance_m": 958.9,
        "geometry_reference": "https://www.openstreetmap.org/way/823272713"
      },
      {
        "osm_id": "way/916863896",
        "name": "Hazira II (Essar) Power Plant",
        "categories": [
          "industrial",
          "powerplant"
        ],
        "distance_m": 1533.4,
        "geometry_reference": "https://www.openstreetmap.org/way/916863896"
      },
      {
        "osm_id": "way/1157017752",
        "name": "Bhander Power Plant",
        "categories": [
          "industrial",
          "powerplant"
        ],
        "distance_m": 1332.4,
        "geometry_reference": "https://www.openstreetmap.org/way/1157017752"
      },
      {
        "osm_id": "way/1187716203",
        "name": null,
        "categories": [
          "industrial"
        ],
        "distance_m": 2596.2,
        "geometry_reference": "https://www.openstreetmap.org/way/1187716203"
      }
    ],
    "coverage_note": "Missing tags or matches do not establish absence; distances limited to query area."
  }
}
```

## Potential evidence to verify manually

These links and search terms are search aids, NOT verified incident evidence. A reviewer must inspect relevance, date, location, and source reliability.

- Coordinates: 21.104560, 72.645415
- [NASA FIRMS map](https://firms.modaps.eosdis.nasa.gov/map/#d:2026-08-17..2026-08-17;@72.645415,21.10456,12z)
- [OpenStreetMap location](https://www.openstreetmap.org/?mlat=21.10456&mlon=72.645415#map=14/21.10456/72.645415)
- [External incident/news search](https://www.google.com/search?q=21.1046+72.6454+fire+2026-08-17)
- Search terms: `21.1046 72.6454 fire 2026-08-17`; optionally add a stored nearby facility name.
