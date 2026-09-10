import csv
import io
import time
from datetime import datetime, timezone, timedelta

import httpx
from shapely.geometry import Point, Polygon, LineString
from shapely.ops import transform
from pyproj import CRS, Transformer

from .config import settings
from .intelligence import validate


_token_cache: dict = {}

USER_AGENT = "ThermaGuardAI-Hackathon/0.1 (SIH 2026 project)"


# ============================================================
# NASA FIRMS
# ============================================================

async def firms(
    bounds,
    days=1,
    start_date=None,
    source="VIIRS_SNPP_NRT",
):
    """
    Retrieve NASA FIRMS thermal anomaly observations.

    Default behavior:
        Near-real-time VIIRS SNPP observations.

    Optional historical behavior:
        Supply start_date='YYYY-MM-DD'
        and an appropriate FIRMS source.

    Existing callers using:
        firms(bounds, days)

    continue to work unchanged.
    """

    if not settings.firms_map_key:
        raise ValueError(
            "FIRMS_MAP_KEY is not configured"
        )

    if not isinstance(bounds, (list, tuple)) or len(bounds) != 4:
        raise ValueError(
            "FIRMS bounds must contain four coordinates"
        )

    if not 1 <= int(days) <= 5:
        raise ValueError(
            "FIRMS day range must be between 1 and 5"
        )

    bbox = ",".join(
        str(value)
        for value in bounds
    )

    url = (
        f"{settings.firms_api_url.rstrip('/')}/"
        f"{settings.firms_map_key}/"
        f"{source}/"
        f"{bbox}/"
        f"{days}"
    )

    if start_date:
        # Validate format before making provider request.
        try:
            datetime.strptime(
                start_date,
                "%Y-%m-%d",
            )
        except ValueError as exc:
            raise ValueError(
                "Historical FIRMS start_date must use YYYY-MM-DD"
            ) from exc

        url += f"/{start_date}"

    async with httpx.AsyncClient(
        timeout=30,
        headers={
            "User-Agent": USER_AGENT,
        },
    ) as client:

        response = await client.get(
            url
        )

        response.raise_for_status()

    reader = csv.DictReader(
        io.StringIO(
            response.text
        )
    )

    required_fields = {
        "latitude",
        "longitude",
        "acq_date",
        "acq_time",
        "frp",
    }

    if not required_fields.issubset(
        reader.fieldnames or []
    ):
        raise ValueError(
            "Invalid FIRMS CSV schema"
        )

    valid = []
    rejected = 0

    for row in reader:
        try:
            valid.append(
                validate(row)
            )

        except (
            ValueError,
            TypeError,
            KeyError,
        ):
            rejected += 1

    if (
        len(valid)
        > settings.max_sync_observations
    ):
        raise ValueError(
            "Observation budget exceeded; "
            "request a smaller region or time range"
        )

    return valid, rejected


# ============================================================
# OPENSTREETMAP / OVERPASS
# ============================================================

async def osm(event):
    """
    Retrieve geospatial context around one thermal event
    using OpenStreetMap / Overpass.
    """

    try:
        lat = float(
            event["latitude"]
        )

        lon = float(
            event["longitude"]
        )

    except (
        KeyError,
        TypeError,
        ValueError,
    ):
        return {
            "osm_context_available": False,
            "reason": "invalid_event_location",
        }

    filters = {
        "industrial":
            '"landuse"="industrial"',

        "refinery":
            '"industrial"="refinery"',

        "powerplant":
            '"power"="plant"',

        "factory":
            '"man_made"="works"',

        "forest":
            '"landuse"="forest"',

        "farmland":
            '"landuse"="farmland"',

        "residential":
            '"landuse"="residential"',
    }

    query = (
        "[out:json][timeout:20];("
        + "".join(
            (
                f"nwr(around:5000,"
                f"{lat},{lon})"
                f"[{tag}];"
            )
            for tag
            in filters.values()
        )
        + ");out geom;"
    )

    try:
        async with httpx.AsyncClient(
            timeout=25,
            headers={
                "User-Agent": USER_AGENT,
            },
        ) as client:

            response = await client.post(
                settings.overpass_api_url,
                data={
                    "data": query
                },
            )

            response.raise_for_status()

        data = response.json()

        if not isinstance(
            data.get("elements"),
            list,
        ):
            raise ValueError(
                "Invalid Overpass response"
            )

        projection = Transformer.from_crs(
            "EPSG:4326",

            CRS.from_proj4(
                (
                    f"+proj=aeqd "
                    f"+lat_0={lat} "
                    f"+lon_0={lon} "
                    f"+datum=WGS84"
                )
            ),

            always_xy=True,
        ).transform

        origin = transform(
            projection,
            Point(
                lon,
                lat,
            ),
        )

        facilities = []

        result = {
            f"distance_to_{key}_m":
                None
            for key
            in filters
        }

        landuses = []

        for item in data["elements"]:

            tags = item.get(
                "tags",
                {},
            )

            geom = item.get(
                "geometry",
                [],
            )

            if geom:

                coords = [
                    (
                        point["lon"],
                        point["lat"],
                    )
                    for point in geom
                ]

                if not coords:
                    continue

                if (
                    len(coords) >= 4
                    and coords[0] == coords[-1]
                ):
                    geometry = Polygon(
                        coords
                    )

                elif len(coords) >= 2:
                    geometry = LineString(
                        coords
                    )

                else:
                    geometry = Point(
                        coords[0]
                    )

            elif (
                "lat" in item
                and "lon" in item
            ):

                geometry = Point(
                    item["lon"],
                    item["lat"],
                )

            else:
                continue

            if not geometry.is_valid:
                continue

            meters = origin.distance(
                transform(
                    projection,
                    geometry,
                )
            )

            categories = []

            for (
                category,
                filter_value,
            ) in filters.items():

                tag_key = (
                    filter_value
                    .split("=")[0]
                    .strip('"')
                )

                tag_value = (
                    filter_value
                    .split("=")[1]
                    .strip('"')
                )

                if (
                    tags.get(tag_key)
                    == tag_value
                ):
                    categories.append(
                        category
                    )

            for category in categories:

                key = (
                    f"distance_to_"
                    f"{category}_m"
                )

                current = result[key]

                if current is None:
                    current = float(
                        "inf"
                    )

                result[key] = round(
                    min(
                        current,
                        meters,
                    ),
                    1,
                )

            if (
                meters == 0
                and tags.get("landuse")
            ):
                landuses.append(
                    tags["landuse"]
                )

            facilities.append(
                {
                    "osm_id":
                        (
                            f"{item['type']}/"
                            f"{item['id']}"
                        ),

                    "name":
                        tags.get("name"),

                    "categories":
                        categories,

                    "distance_m":
                        round(
                            meters,
                            1,
                        ),

                    "geometry_reference":
                        (
                            "https://www.openstreetmap.org/"
                            f"{item['type']}/"
                            f"{item['id']}"
                        ),
                }
            )

        return {
            **result,

            "osm_context_available":
                True,

            # Keep legacy source for current frontend/API.
            "source":
                "OpenStreetMap Overpass",

            # Explicit source avoids ambiguity when
            # OSM and satellite dictionaries are merged.
            "osm_source":
                "OpenStreetMap Overpass",

            "retrieved_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            "osm_retrieved_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            "search_radius_m":
                5000,

            "landuse_class":
                (
                    landuses[0]
                    if landuses
                    else None
                ),

            "nearby_facility_count":
                len(
                    facilities
                ),

            "nearby_industrial_count":
                sum(
                    (
                        "industrial"
                        in facility[
                            "categories"
                        ]
                    )
                    for facility
                    in facilities
                ),

            "facilities":
                facilities[:50],

            "coverage_note":
                (
                    "Missing tags or matches do not "
                    "establish absence; distances "
                    "limited to query area."
                ),

            "osm_reason":
                None,
        }

    except httpx.HTTPStatusError as exc:

        status = (
            exc.response.status_code
        )

        if status >= 500:
            reason = (
                "osm_provider_unavailable"
            )

        else:
            reason = (
                "osm_request_failed"
            )

        return {
            "osm_context_available":
                False,

            "reason":
                reason,

            "osm_reason":
                reason,
        }

    except (
        httpx.HTTPError,
        ValueError,
        KeyError,
        TypeError,
    ):

        return {
            "osm_context_available":
                False,

            "reason":
                "OSM unavailable or invalid response",

            "osm_reason":
                "OSM unavailable or invalid response",
        }


# ============================================================
# COPERNICUS OAUTH
# ============================================================

async def _copernicus_token(
    unavailable,
):
    """
    Obtain or reuse a Copernicus OAuth access token.
    """

    monotonic_now = (
        time.monotonic()
    )

    token = _token_cache.get(
        "token"
    )

    token_expires = (
        _token_cache.get(
            "expires",
            0,
        )
    )

    if (
        token
        and monotonic_now
        < token_expires
    ):
        return token, None

    try:
        async with httpx.AsyncClient(
            timeout=20,
            headers={
                "User-Agent":
                    USER_AGENT,
            },
        ) as client:

            response = await client.post(
                settings.copernicus_token_url,

                data={
                    "grant_type":
                        "client_credentials",

                    "client_id":
                        settings.copernicus_client_id,

                    "client_secret":
                        settings.copernicus_client_secret,
                },

                headers={
                    "Content-Type":
                        (
                            "application/"
                            "x-www-form-urlencoded"
                        )
                },
            )

            response.raise_for_status()

            payload = response.json()

        token = payload[
            "access_token"
        ]

        expires_in = int(
            payload.get(
                "expires_in",
                300,
            )
        )

        _token_cache.update(
            token=token,

            expires=(
                monotonic_now
                + max(
                    60,
                    expires_in - 30,
                )
            ),
        )

        return token, None

    except httpx.HTTPStatusError as exc:

        _token_cache.clear()

        status = (
            exc.response.status_code
        )

        print(
            "Copernicus OAuth error:",
            status,
            exc.response.text[:300],
        )

        if status >= 500:
            reason = (
                "provider_unavailable"
            )

        else:
            reason = (
                "oauth_failed"
            )

        return (
            None,
            {
                **unavailable,
                "reason": reason,
            },
        )

    except (
        httpx.HTTPError,
        ValueError,
        KeyError,
        TypeError,
    ) as exc:

        _token_cache.clear()

        print(
            "Copernicus OAuth failure:",
            type(exc).__name__,
            str(exc)[:200],
        )

        return (
            None,
            {
                **unavailable,
                "reason":
                    "provider_unavailable",
            },
        )


# ============================================================
# COPERNICUS / SENTINEL-2 SATELLITE CONTEXT
# ============================================================

async def satellite(
    event=None,
):
    """
    Retrieve real Sentinel-2 L2A statistical context
    from Copernicus Data Space.

    Current feature:
        Mean NDVI around the thermal event.

    No full satellite scene is downloaded.
    No fabricated satellite values are produced.
    """

    unavailable = {
        "satellite_context_available":
            False,

        "ndvi":
            None,

        "land_cover":
            None,

        "vegetation_fraction":
            None,

        "built_up_fraction":
            None,

        "satellite_image_reference":
            None,

        "provider":
            "copernicus",
    }

    # --------------------------------------------------------
    # Configuration validation
    # --------------------------------------------------------

    if (
        settings.satellite_provider.lower()
        != "copernicus"
    ):
        return {
            **unavailable,

            "reason":
                "unsupported_satellite_provider",
        }

    if (
        not settings
        .satellite_credentials_present
    ):
        return {
            **unavailable,

            "reason":
                "credentials_missing",
        }

    if event is None:
        return {
            **unavailable,

            "reason":
                "event_missing",
        }

    # --------------------------------------------------------
    # Event location
    # --------------------------------------------------------

    try:
        latitude = float(
            event["latitude"]
        )

        longitude = float(
            event["longitude"]
        )

        if not (
            -90
            <= latitude
            <= 90
        ):
            raise ValueError(
                "Invalid latitude"
            )

        if not (
            -180
            <= longitude
            <= 180
        ):
            raise ValueError(
                "Invalid longitude"
            )

    except (
        KeyError,
        TypeError,
        ValueError,
    ):
        return {
            **unavailable,

            "reason":
                "invalid_event_location",
        }

    # --------------------------------------------------------
    # Event time
    # --------------------------------------------------------

    try:
        event_time = (
            datetime.fromisoformat(
                event[
                    "last_seen_time"
                ]
            )
        )

        if event_time.tzinfo is None:

            event_time = (
                event_time.replace(
                    tzinfo=timezone.utc
                )
            )

        else:

            event_time = (
                event_time.astimezone(
                    timezone.utc
                )
            )

    except (
        KeyError,
        TypeError,
        ValueError,
    ):
        return {
            **unavailable,

            "reason":
                "invalid_event_time",
        }

    # --------------------------------------------------------
    # OAuth
    # --------------------------------------------------------

    token, token_error = (
        await _copernicus_token(
            unavailable
        )
    )

    if token_error:
        return token_error

    # --------------------------------------------------------
    # Sentinel-2 observation time window
    # --------------------------------------------------------

    event_day = (
        event_time.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
    )

    window_start = (
        event_day
        - timedelta(
            days=7
        )
    )

    window_end = (
        event_day
        + timedelta(
            days=7
        )
    )

    current_utc = (
        datetime.now(
            timezone.utc
        )
    )

    if (
        window_end
        > current_utc
    ):
        window_end = (
            current_utc
        )

    if (
        window_end
        <= window_start
    ):
        return {
            **unavailable,

            "reason":
                "invalid_satellite_time_window",
        }

    # --------------------------------------------------------
    # ~4 km wide AOI around event
    # --------------------------------------------------------

    bbox = [
        longitude - 0.02,
        latitude - 0.02,
        longitude + 0.02,
        latitude + 0.02,
    ]

    # --------------------------------------------------------
    # NDVI evalscript
    # --------------------------------------------------------

    evalscript = """
//VERSION=3

function setup() {
    return {
        input: [{
            bands: [
                "B04",
                "B08",
                "dataMask"
            ]
        }],
        output: [
            {
                id: "ndvi",
                bands: 1,
                sampleType: "FLOAT32"
            },
            {
                id: "dataMask",
                bands: 1
            }
        ]
    };
}

function evaluatePixel(sample) {

    let denominator =
        sample.B08
        + sample.B04;

    if (denominator === 0) {

        return {
            ndvi: [0],
            dataMask: [0]
        };
    }

    let ndvi =
        (
            sample.B08
            - sample.B04
        )
        / denominator;

    return {
        ndvi: [ndvi],
        dataMask: [
            sample.dataMask
        ]
    };
}
"""

    # --------------------------------------------------------
    # Statistical API request
    # --------------------------------------------------------

    request = {
        "input": {

            "bounds": {

                "bbox":
                    bbox,

                "properties": {
                    "crs":
                        (
                            "http://www.opengis.net/"
                            "def/crs/EPSG/0/4326"
                        )
                },
            },

            "data": [
                {
                    "type":
                        "sentinel-2-l2a",

                    "dataFilter": {

                        "mosaickingOrder":
                            "leastCC",

                        "maxCloudCoverage":
                            80,
                    },
                }
            ],
        },

        "aggregation": {

            "timeRange": {

                "from":
                    (
                        window_start
                        .isoformat()
                        .replace(
                            "+00:00",
                            "Z",
                        )
                    ),

                "to":
                    (
                        window_end
                        .isoformat()
                        .replace(
                            "+00:00",
                            "Z",
                        )
                    ),
            },

            "aggregationInterval": {
                "of": "P1D"
            },

            # EPSG:4326 uses degrees.
            # ~0.0002 degrees is roughly
            # 20-22 metres in this region.
            "resx":
                0.0002,

            "resy":
                0.0002,

            "evalscript":
                evalscript,
        },
    }

    statistics_url = (
        settings
        .copernicus_base_url
        .rstrip("/")
        + "/statistics/v1"
    )

    # --------------------------------------------------------
    # Statistical API call
    # --------------------------------------------------------

    try:
        async with httpx.AsyncClient(
            timeout=45,

            headers={
                "User-Agent":
                    USER_AGENT,

                "Authorization":
                    f"Bearer {token}",

                "Accept":
                    "application/json",

                "Content-Type":
                    "application/json",
            },
        ) as client:

            response = await client.post(
                statistics_url,
                json=request,
            )

            response.raise_for_status()

            data = response.json()

    except httpx.HTTPStatusError as exc:

        status = (
            exc.response.status_code
        )

        print(
            "Copernicus Statistical API error:",
            status,
            exc.response.text[:500],
        )

        # Server/provider errors mean provider unavailable.
        if status >= 500:

            reason = (
                "provider_unavailable"
            )

        # Authentication/authorization problem.
        elif status in {
            401,
            403,
        }:

            reason = (
                "provider_auth_failed"
            )

        # Bad request, unsupported payload, etc.
        else:

            reason = (
                "statistics_request_failed"
            )

        return {
            **unavailable,

            "reason":
                reason,
        }

    except httpx.HTTPError as exc:

        print(
            "Copernicus connection error:",
            type(exc).__name__,
            str(exc)[:300],
        )

        return {
            **unavailable,

            "reason":
                "provider_unavailable",
        }

    except (
        ValueError,
        KeyError,
        TypeError,
    ) as exc:

        print(
            "Copernicus response parsing error:",
            type(exc).__name__,
            str(exc)[:300],
        )

        return {
            **unavailable,

            "reason":
                "invalid_provider_response",
        }

    # --------------------------------------------------------
    # Parse Statistical API response
    # --------------------------------------------------------

    intervals = (
        data.get(
            "data"
        )
        or []
    )

    valid_observations = []

    for interval in intervals:

        stats = (
            interval
            .get(
                "outputs",
                {},
            )
            .get(
                "ndvi",
                {},
            )
            .get(
                "bands",
                {},
            )
            .get(
                "B0",
                {},
            )
            .get(
                "stats",
                {},
            )
        )

        if not stats:
            continue

        sample_count = (
            stats.get(
                "sampleCount",
                0,
            )
        )

        no_data_count = (
            stats.get(
                "noDataCount",
                0,
            )
        )

        mean = stats.get(
            "mean"
        )

        if (
            mean is not None
            and sample_count
            > no_data_count
        ):

            interval_date = (
                interval
                .get(
                    "interval",
                    {},
                )
                .get(
                    "from",
                    "",
                )[:10]
            )

            valid_observations.append(
                {
                    "mean":
                        float(
                            mean
                        ),

                    "date":
                        interval_date,

                    "sample_count":
                        sample_count,

                    "no_data_count":
                        no_data_count,
                }
            )

    if not valid_observations:

        return {
            **unavailable,

            "reason":
                "no_sentinel2_observation_available",
        }

    # --------------------------------------------------------
    # Select observation closest to FIRMS event
    # --------------------------------------------------------

    def observation_distance(
        observation,
    ):
        try:
            observation_date = (
                datetime
                .fromisoformat(
                    observation[
                        "date"
                    ]
                )
                .date()
            )

            return abs(
                (
                    observation_date
                    - event_time.date()
                ).days
            )

        except (
            ValueError,
            TypeError,
        ):
            return 99999

    selected = min(
        valid_observations,
        key=observation_distance,
    )

    ndvi = (
        selected["mean"]
    )

    # --------------------------------------------------------
    # Validate NDVI
    # --------------------------------------------------------

    if not (
        -1.0
        <= ndvi
        <= 1.0
    ):
        return {
            **unavailable,

            "reason":
                "invalid_ndvi_value",
        }

    retrieved_at = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    # --------------------------------------------------------
    # Success
    # --------------------------------------------------------

    return {
        **unavailable,

        "satellite_context_available":
            True,

        "ndvi":
            round(
                ndvi,
                4,
            ),

        "acquisition_date":
            selected[
                "date"
            ],

        "satellite_image_reference":
            (
                "Sentinel-2 L2A via "
                "Copernicus Data Space "
                "Sentinel Hub Statistical API"
            ),

        "provider":
            "copernicus",

        # Explicitly clear any old failure state.
        "reason":
            None,

        # Legacy compatibility.
        "source":
            (
                "Copernicus Data Space "
                "Ecosystem"
            ),

        # Prefer these explicit fields in future API/UI.
        "satellite_source":
            (
                "Copernicus Data Space "
                "Ecosystem"
            ),

        "retrieved_at":
            retrieved_at,

        "satellite_retrieved_at":
            retrieved_at,

        "search_radius_note":
            "~2 km around event center",

        "observation_sample_count":
            selected[
                "sample_count"
            ],
    }


# ============================================================
# SATELLITE UNAVAILABLE HELPER
# ============================================================

async def satellite_unavailable():
    """
    Explicit satellite-unavailability result.

    Used when live satellite context should not be queried,
    including demo mode or missing configuration.
    """

    if settings.demo_mode:

        reason = (
            "demo_mode"
        )

    elif (
        settings
        .satellite_provider
        .lower()
        != "copernicus"
    ):

        reason = (
            "unsupported_satellite_provider"
        )

    elif (
        not settings
        .satellite_credentials_present
    ):

        reason = (
            "credentials_missing"
        )

    else:

        reason = (
            "event_missing"
        )

    return {
        "satellite_context_available":
            False,

        "ndvi":
            None,

        "land_cover":
            None,

        "vegetation_fraction":
            None,

        "built_up_fraction":
            None,

        "satellite_image_reference":
            None,

        "provider":
            settings.satellite_provider,

        "reason":
            reason,
    }