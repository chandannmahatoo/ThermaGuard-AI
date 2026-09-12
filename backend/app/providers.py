import csv
import asyncio
import logging
import math
import io
import time
from datetime import datetime, timezone, timedelta

import httpx
from shapely.geometry import Point, Polygon, LineString
from shapely.ops import transform
from pyproj import CRS, Transformer

from .config import settings, FIRMS_SOURCES
from .intelligence import validate


_token_cache: dict = {}
logger = logging.getLogger(__name__)

USER_AGENT = "ThermaGuardAI-Hackathon/0.1 (SIH 2026 project)"


# ============================================================
# NASA FIRMS
# ============================================================

class SourceUnavailable(ValueError):
    """A valid source selection cannot be served for the requested date window."""


_availability_cache = {}
_availability_lock = asyncio.Lock()


async def _firms_sources_impl():
    """Five-minute, single-flight availability cache; never return stale data on failure."""
    if not settings.firms_map_key:
        raise ValueError('FIRMS credentials unavailable')
    key = (settings.firms_availability_url, settings.firms_map_key)
    async with _availability_lock:
        if _availability_cache.get('key') == key and time.monotonic() < _availability_cache.get('expires', 0):
            return [dict(row) for row in _availability_cache['sources']]
        async with httpx.AsyncClient(timeout=settings.firms_timeout_seconds, headers={'User-Agent': USER_AGENT}) as client:
            response = await asyncio.wait_for(client.get(
                settings.firms_availability_url.rstrip('/')+'/'+settings.firms_map_key+'/all'), settings.firms_timeout_seconds)
            response.raise_for_status()
        reader = csv.DictReader(io.StringIO(response.text))
        if not {'data_id', 'min_date', 'max_date'}.issubset(reader.fieldnames or []):
            raise ValueError('Invalid FIRMS availability schema')
        sources = {}
        for row in reader:
            source = row['data_id']
            if source not in FIRMS_SOURCES:
                continue  # Burned-area/GOES/Landsat products need different schemas.
            low = datetime.strptime(row['min_date'], '%Y-%m-%d').date()
            high = datetime.strptime(row['max_date'], '%Y-%m-%d').date()
            if low > high or source in sources:
                raise ValueError('Invalid FIRMS availability range or duplicate source')
            sources[source] = dict(id=source, min_date=low.isoformat(), max_date=high.isoformat(), kind=FIRMS_SOURCES[source][0])
        if not sources:
            raise ValueError('No supported FIRMS hotspot sources available')
        result = sorted(sources.values(), key=lambda row: row['id'])
        _availability_cache.update(key=key, sources=result, expires=time.monotonic()+300)
        return [dict(row) for row in result]


async def check_firms_window(source, days, start_date=None):
    if source not in FIRMS_SOURCES:
        raise SourceUnavailable('Unsupported FIRMS source')
    available = {row['id']: row for row in await firms_sources()}
    if source not in available:
        raise SourceUnavailable('FIRMS source is currently unavailable')
    end = datetime.now(timezone.utc).date()
    start = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else end-timedelta(days=days-1)
    if start_date:
        end = start+timedelta(days=days-1)
    row = available[source]
    if start.isoformat() < row['min_date'] or end.isoformat() > row['max_date']:
        raise SourceUnavailable('Requested dates are outside FIRMS source availability')


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

    if source not in FIRMS_SOURCES:
        raise SourceUnavailable('Unsupported FIRMS source')
    if not settings.firms_map_key:
        raise ValueError('FIRMS_MAP_KEY is not configured')

    if not isinstance(bounds, (list, tuple)) or len(bounds) != 4:
        raise ValueError(
            "FIRMS bounds must contain four coordinates"
        )

    if (not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in bounds)
            or not (-180 <= bounds[0] < bounds[2] <= 180 and -90 <= bounds[1] < bounds[3] <= 90)):
        raise ValueError('Invalid FIRMS bounds')
    if not isinstance(days, int) or isinstance(days, bool) or not 1 <= days <= 5:
        raise ValueError(
            "FIRMS day range must be between 1 and 5"
        )

    await check_firms_window(source, days, start_date)

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
        timeout=settings.firms_timeout_seconds,
        headers={
            "User-Agent": USER_AGENT,
        },
    ) as client:

        response = await asyncio.wait_for(client.get(url), settings.firms_timeout_seconds)

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

    end_day = datetime.now(timezone.utc).date()
    start_day = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else end_day-timedelta(days=days-1)
    if start_date:
        end_day = start_day+timedelta(days=days-1)
    valid = []
    rejected = 0

    for row in reader:
        try:
            observation = validate(row, source_dataset=source)
            day = datetime.fromisoformat(observation['observed_at']).date()
            if not (bounds[0] <= observation['longitude'] <= bounds[2]
                    and bounds[1] <= observation['latitude'] <= bounds[3]
                    and start_day <= day <= end_day):
                raise ValueError('Observation is outside requested bounds or dates')
            valid.append(observation)

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

async def _osm_request(event):
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
            timeout=settings.osm_timeout_seconds,
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

_token_lock = asyncio.Lock()


async def _copernicus_token(unavailable, rejected_token=None):
    """Single-flight OAuth refresh; a stale 401 cannot invalidate a newer token."""
    async with _token_lock:
        if rejected_token and _token_cache.get('token') == rejected_token:
            _token_cache.clear()
        if _token_cache.get('token') and time.monotonic() < _token_cache.get('expires', 0):
            return _token_cache['token'], None
        if time.monotonic() < _token_cache.get('retry_after', 0):
            return None, {**unavailable, 'reason': _token_cache['failure_reason']}
        try:
            async with httpx.AsyncClient(timeout=settings.copernicus_token_timeout_seconds,
                                         headers={'User-Agent': USER_AGENT}) as client:
                response = await asyncio.wait_for(client.post(settings.copernicus_token_url,
                    data={'grant_type': 'client_credentials', 'client_id': settings.copernicus_client_id,
                          'client_secret': settings.copernicus_client_secret},
                    headers={'Content-Type': 'application/x-www-form-urlencoded'}),
                    settings.copernicus_token_timeout_seconds)
                response.raise_for_status()
                payload = response.json()
            token = payload['access_token']
            expires = float(payload.get('expires_in', 300))
            if not isinstance(token, str) or not token.strip() or not math.isfinite(expires) or expires <= 0:
                raise ValueError('Invalid OAuth response')
            _token_cache.update(token=token, expires=time.monotonic()+expires-min(30, expires/10))
            return token, None
        except httpx.HTTPStatusError as exc:
            reason = 'provider_unavailable' if exc.response.status_code >= 500 else 'oauth_failed'
            logger.warning('Copernicus OAuth HTTP status=%d', exc.response.status_code)
        except (httpx.HTTPError, TimeoutError, ValueError, KeyError, TypeError):
            reason = 'provider_unavailable'
            logger.warning('Copernicus OAuth unavailable or invalid response')
        _token_cache.clear()
        _token_cache.update(retry_after=time.monotonic()+1, failure_reason=reason)
        return None, {**unavailable, 'reason': reason}


async def _statistics_response(url, request, token, unavailable):
    for attempt in range(2):
        async with httpx.AsyncClient(timeout=settings.copernicus_stats_timeout_seconds,
            headers={'User-Agent': USER_AGENT, 'Authorization': f'Bearer {token}',
                     'Accept': 'application/json', 'Content-Type': 'application/json'}) as client:
            response = await asyncio.wait_for(client.post(url, json=request), settings.copernicus_stats_timeout_seconds)
        if response.status_code in (401, 403) and attempt == 0:
            token, error = await _copernicus_token(unavailable, rejected_token=token)
            if error:
                return None, error
            continue
        response.raise_for_status()
        return response.json(), None


# ============================================================
# COPERNICUS / SENTINEL-2 SATELLITE CONTEXT
# ============================================================

async def _satellite_request(
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
                0.00018,

            "resy":
                0.00018,

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
        data, token_error = await _statistics_response(statistics_url, request, token, unavailable)
        if token_error:
            return token_error

    except httpx.HTTPStatusError as exc:

        status = (
            exc.response.status_code
        )

        logger.warning('Copernicus statistics HTTP status=%d', status)

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

    except (httpx.HTTPError, TimeoutError):

        logger.warning('Copernicus statistics unavailable')

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

        logger.warning('Copernicus statistics invalid response')

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
# Additional context is evidence only. No imports from the classifier/risk engine.
from copy import deepcopy
from collections import OrderedDict
from pathlib import Path
import json
import threading

CONTEXT_NAMES = ('weather', 'air_quality', 'location', 'eonet', 'routing')
CONTEXT_PREFIX = {'location': 'geocoding', 'routing': 'routing'}
CONTEXT_TTL = {'weather': 3600, 'air_quality': 3600, 'location': 30*86400, 'eonet': 3600, 'routing': 86400}
CONTEXT_FIELDS = {
    'weather': ('temperature_c','relative_humidity_percent','precipitation_mm','wind_speed_kmh','wind_direction_deg','observed_at','data_kind','weather_dataset','attribution'),
    'air_quality': ('pm2_5','pm10','carbon_monoxide','nitrogen_dioxide','ozone','units','observed_at','data_kind','attribution'),
    'location': ('display_name','city','district','state','country','country_code','attribution'),
    'eonet': ('matched','event_id','title','category','distance_km','event_date','source','match_radius_km','match_window_hours'),
    'routing': ('distance_m','duration_seconds','origin','destination','profile','attribution'),
}
_context_cache = OrderedDict()
_nominatim_lock = asyncio.Lock()
_nominatim_last = 0.0


def utc_now():
    return datetime.now(timezone.utc)


def context_status(name, status='unavailable', reason='not_available'):
    return dict(provider={'weather':'open_meteo','air_quality':'open_meteo','location':'nominatim',
                          'eonet':'nasa_eonet','routing':'openrouteservice'}[name],
                status=status, reason=reason, fetched_at=utc_now().isoformat(), version=1)


def event_time(event):
    value = datetime.fromisoformat(event['last_seen_time'].replace('Z', '+00:00'))
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def coordinates(event):
    lat, lon = event['latitude'], event['longitude']
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in (lat, lon)):
        raise ValueError('Invalid coordinates')
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError('Invalid coordinates')
    return lat, lon


def _weather_endpoint(observed: datetime) -> str:
    """Select the correct Open-Meteo endpoint for the event timestamp."""
    age_seconds = (utc_now() - observed).total_seconds()
    if age_seconds > 7 * 86400:
        return settings.weather_historical_api_url
    return settings.weather_api_url


def context_signature(name, event, destination=None):
    lat, lon = coordinates(event)

    if name == "routing":
        endpoint = settings.openrouteservice_api_url

    elif name == "weather":
        observed = event_time(event)
        endpoint = _weather_endpoint(observed)

    else:
        prefix = CONTEXT_PREFIX.get(name, name)
        endpoint = getattr(
            settings,
            prefix + "_api_url",
        )

    signature = [
        round(lat, 5),
        round(lon, 5),
        endpoint,
    ]

    if name in ("weather", "air_quality"):
        observed = event_time(event).replace(
            minute=0,
            second=0,
            microsecond=0,
        )
        signature.append(
            observed.isoformat()
        )

    elif name == "eonet":
        signature.append(
            event_time(event).isoformat()
        )

    if name == "routing":
        signature.append(
            list(destination)
            if destination is not None
            else None
        )

    return signature


def fresh_context(name, packet, signature):
    if not isinstance(packet, dict) or packet.get('status') != 'available' or packet.get('signature') != signature or packet.get('version') != 1:
        return False
    try:
        age = (utc_now()-datetime.fromisoformat(packet['fetched_at'])).total_seconds()
        return 0 <= age < CONTEXT_TTL[name]
    except (ValueError, KeyError, TypeError):
        return False


async def nominatim_get(url, params, timeout, user_agent):
    """Shared one-request/second gate for forward and reverse geocoding (one worker)."""
    global _nominatim_last
    async with _nominatim_lock:
        await asyncio.sleep(max(0, 1.1-(time.monotonic()-_nominatim_last)))
        _nominatim_last = time.monotonic()
        return await _context_json(url, params, timeout, {'User-Agent': user_agent}, provider='location')


async def _context_json(url, params, timeout, headers=None, body=None, provider=None):
    started = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=timeout, headers={'User-Agent':USER_AGENT, **(headers or {})}) as client:
            request = client.get(url, params=params) if body is None else client.post(url, json=body)
            response = await asyncio.wait_for(request, timeout)
            response.raise_for_status()
            payload = response.json()
        if provider:
            record_provider_call(provider, 'success', time.monotonic()-started)
        return payload
    except Exception as exc:
        if provider:
            record_provider_call(provider, 'failure', time.monotonic()-started, _safe_category(exc))
        raise


def number(value, low=None, high=None):
    if isinstance(value, bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        raise ValueError('Invalid numeric observation')
    if (low is not None and value < low) or (high is not None and value > high):
        raise ValueError('Out of range observation')
    return value


async def _hourly_context(event, name):
    """Fetch hourly weather or air-quality evidence for the exact event hour."""
    lat, lon = coordinates(event)
    observed = event_time(event).replace(minute=0, second=0, microsecond=0)

    if name == 'weather':
        fields = {
            'temperature_2m': ('temperature_c', -100, 70),
            'relative_humidity_2m': ('relative_humidity_percent', 0, 100),
            'precipitation': ('precipitation_mm', 0, None),
            'wind_speed_10m': ('wind_speed_kmh', 0, None),
            'wind_direction_10m': ('wind_direction_deg', 0, 360),
        }
    elif name == 'air_quality':
        fields = {
            key: (key, 0, None)
            for key in ('pm2_5', 'pm10', 'carbon_monoxide', 'nitrogen_dioxide', 'ozone')
        }
    else:
        raise ValueError('Unsupported hourly context provider')

    event_date = observed.date().isoformat()
    params = dict(
        latitude=lat,
        longitude=lon,
        hourly=','.join(fields),
        timezone='GMT',
        start_date=event_date,
        end_date=event_date,
    )

    if name == 'weather':
        params.update(
            temperature_unit='celsius',
            wind_speed_unit='kmh',
            precipitation_unit='mm',
        )
        api_url = _weather_endpoint(observed)
        timeout = settings.weather_timeout_seconds
    else:
        api_url = settings.air_quality_api_url
        timeout = settings.air_quality_timeout_seconds

    data = await _context_json(api_url, params, timeout, provider=name)
    if not isinstance(data, dict):
        raise ValueError('Invalid provider response')

    hourly = data.get('hourly')
    if not isinstance(hourly, dict):
        raise ValueError('Missing hourly observations')

    times = hourly.get('time')
    if not isinstance(times, list):
        raise ValueError('Invalid time array')

    index = None
    for i, value in enumerate(times):
        if not isinstance(value, str):
            continue
        try:
            provider_time = datetime.fromisoformat(value.replace('Z', '+00:00'))
            if provider_time.tzinfo is None:
                provider_time = provider_time.replace(tzinfo=timezone.utc)
            else:
                provider_time = provider_time.astimezone(timezone.utc)
        except ValueError:
            continue
        if provider_time == observed:
            index = i
            break

    if index is None:
        return context_status(name, reason='event_hour_unavailable')

    output = {}
    for key, (internal, low, high) in fields.items():
        values = hourly.get(key)
        if not isinstance(values, list) or len(values) != len(times):
            raise ValueError(f'Invalid hourly array: {key}')
        value = values[index]
        output[internal] = None if value is None else number(value, low, high)

    if not any(value is not None for value in output.values()):
        return context_status(name, reason='no_observations')

    units = data.get('hourly_units')
    if not isinstance(units, dict):
        raise ValueError('Missing hourly units')

    if name == 'weather':
        expected_units = {
            'temperature_2m': '°C',
            'relative_humidity_2m': '%',
            'precipitation': 'mm',
            'wind_speed_10m': 'km/h',
            'wind_direction_10m': '°',
        }
    else:
        expected_units = {key: 'μg/m³' for key in fields}

    for key, expected_unit in expected_units.items():
        if units.get(key) != expected_unit:
            raise ValueError(f'Unexpected unit for {key}: {units.get(key)!r}')

    if name == 'weather':
        output.update(
            observed_at=observed.isoformat(),
            data_kind='modelled_grid_context',
            weather_dataset=(
                'historical_forecast'
                if api_url == settings.weather_historical_api_url
                else 'forecast'
            ),
            attribution='Open-Meteo',
        )
    else:
        output.update(
            observed_at=observed.isoformat(),
            data_kind='modelled_grid_context',
            attribution='Open-Meteo / Copernicus CAMS',
            units='μg/m³',
        )

    return {**context_status(name, 'available', None), **output}


async def _reverse_geocode(event):
    lat,lon=coordinates(event)
    data=await nominatim_get(settings.geocoding_api_url,dict(lat=lat,lon=lon,format='jsonv2',addressdetails=1),
                             settings.geocoding_timeout_seconds,settings.geocoding_user_agent)
    if not isinstance(data,dict):raise ValueError('Invalid geocoding response')
    if data.get('error'):return context_status('location',reason='no_address')
    address=data.get('address') or {}
    if not isinstance(address,dict) or not isinstance(data.get('display_name'),str) or not data['display_name'].strip():
        raise ValueError('Missing address')
    def text(key):
        value=address.get(key)
        return value[:500] if isinstance(value,str) else None
    return {**context_status('location','available',None),'display_name':data['display_name'][:1000],
            'city':text('city') or text('town') or text('village'),'district':text('state_district') or text('county'),
            'state':text('state'),'country':text('country'),'country_code':text('country_code'),
            'attribution':'© OpenStreetMap contributors (ODbL)'}


def haversine_km(lat,lon,other_lat,other_lon):
    dlat,dlon=math.radians(other_lat-lat), math.radians(other_lon-lon)
    a=math.sin(dlat/2)**2+math.cos(math.radians(lat))*math.cos(math.radians(other_lat))*math.sin(dlon/2)**2
    return 6371.0088*2*math.asin(math.sqrt(min(1,max(0,a))))


async def _eonet_context(event):
    lat,lon=coordinates(event); observed=event_time(event)
    # A bounded 50 km / 72 h supporting-evidence match, including closed events.
    params=dict(status='all',start=(observed-timedelta(days=3)).date().isoformat(),
                end=(observed+timedelta(days=3)).date().isoformat())
    data=await _context_json(settings.eonet_api_url,params,settings.eonet_timeout_seconds,provider='eonet')
    if not isinstance(data,dict) or not isinstance(data.get('events'),list):raise ValueError('Invalid EONET response')
    matches=[]
    for item in data['events']:
        if not isinstance(item,dict) or not isinstance(item.get('geometry'),list):raise ValueError('Invalid EONET event')
        for geometry in item['geometry']:
            if geometry.get('type')!='Point':continue  # Unsupported shapes are never approximated as points.
            xy=geometry['coordinates']; x,y=xy
            coordinates({'latitude':y,'longitude':x})
            date=datetime.fromisoformat(geometry['date'].replace('Z','+00:00'))
            if date.tzinfo is None:date=date.replace(tzinfo=timezone.utc)
            distance=haversine_km(lat,lon,y,x)
            if distance<=50 and abs((date-observed).total_seconds())<=72*3600:
                categories=item.get('categories',[])
                if not isinstance(item.get('id'),str) or not isinstance(item.get('title'),str):raise ValueError('Invalid EONET identity')
                matches.append(dict(matched=True,event_id=item['id'],title=item['title'][:500],
                    category=', '.join(c['title'] for c in categories if isinstance(c.get('title'),str)),
                    distance_km=round(distance,3),event_date=date.isoformat(),source='NASA EONET'))
    result=min(matches,key=lambda x:x['distance_km']) if matches else {'matched':False}
    return {**context_status('eonet','available',None),**result,'match_radius_km':50,'match_window_hours':72}


async def _route_context(event, destination):
    """Fetch an OpenRouteService driving route for one event.

    ORS error code 2010 means the request was valid but one or more
    coordinates could not be snapped to the routing graph. That is an
    expected operational outcome for remote thermal detections, not a
    malformed provider response.

    Strategy:
      1. Try the normal ORS snapping radius.
      2. If ORS returns code 2010, retry once with a 2 km radius.
      3. If code 2010 remains, return a clean ``unavailable`` packet.
    """
    lat, lon = coordinates(event)
    dest_lon, dest_lat = destination
    coordinates({'latitude': dest_lat, 'longitude': dest_lon})

    url = (
        settings.openrouteservice_api_url.rstrip('/')
        + '/v2/directions/driving-car/geojson'
    )
    headers = {
        'Authorization': settings.openrouteservice_api_key,
        'Content-Type': 'application/json',
    }

    async def request_route(radiuses=None):
        body = {
            'coordinates': [
                [lon, lat],
                [dest_lon, dest_lat],
            ],
            'instructions': False,
        }
        if radiuses is not None:
            body['radiuses'] = radiuses

        started = time.monotonic()

        try:
            async with httpx.AsyncClient(
                timeout=settings.routing_timeout_seconds,
                headers={
                    'User-Agent': USER_AGENT,
                    **headers,
                },
            ) as client:
                response = await asyncio.wait_for(
                    client.post(url, json=body),
                    settings.routing_timeout_seconds,
                )

            # ORS returns useful structured JSON for routing-domain failures
            # such as "no routable point nearby", often with HTTP 4xx.
            try:
                payload = response.json()
            except ValueError:
                response.raise_for_status()
                raise ValueError('Invalid OpenRouteService JSON response')

            if not isinstance(payload, dict):
                raise ValueError('Invalid OpenRouteService response')

            error = payload.get('error')
            if isinstance(error, dict):
                code = error.get('code')

                if code == 2010:
                    # Provider is reachable and behaving correctly. The
                    # requested point is simply not close enough to its
                    # routable road graph.
                    record_provider_call(
                        'routing',
                        'success',
                        time.monotonic() - started,
                    )
                    return None, code

                # Other provider errors should retain normal HTTP semantics.
                response.raise_for_status()
                raise ValueError('OpenRouteService returned an error response')

            response.raise_for_status()

            record_provider_call(
                'routing',
                'success',
                time.monotonic() - started,
            )
            return payload, None

        except Exception as exc:
            record_provider_call(
                'routing',
                'failure',
                time.monotonic() - started,
                _safe_category(exc),
            )
            raise

    data, error_code = await request_route()

    # FIRMS detections may be well away from roads. Retry once with a
    # bounded 2 km snapping radius before declaring routing unavailable.
    if error_code == 2010:
        data, error_code = await request_route([2000, 2000])

    if error_code == 2010:
        return {
            **context_status(
                'routing',
                'unavailable',
                'no_routable_point_near_event',
            ),
            'origin': [lon, lat],
            'destination': [dest_lon, dest_lat],
            'profile': 'driving-car',
            'snap_radius_m': 2000,
            'attribution': (
                'openrouteservice / © OpenStreetMap contributors'
            ),
        }

    if not isinstance(data, dict):
        raise ValueError('Invalid OpenRouteService response')

    features = data.get('features')
    if not isinstance(features, list) or not features:
        raise ValueError('Missing route features')

    feature = features[0]
    if not isinstance(feature, dict):
        raise ValueError('Invalid route feature')

    properties = feature.get('properties')
    geometry = feature.get('geometry')

    if not isinstance(properties, dict):
        raise ValueError('Missing route properties')

    summary = properties.get('summary')
    if not isinstance(summary, dict):
        raise ValueError('Missing route summary')

    if not isinstance(geometry, dict):
        raise ValueError('Missing route geometry')

    if (
        geometry.get('type') != 'LineString'
        or not isinstance(geometry.get('coordinates'), list)
    ):
        raise ValueError('Invalid route')

    route_coordinates = geometry['coordinates']
    if len(route_coordinates) < 2:
        raise ValueError('Empty route')

    for point in route_coordinates:
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ValueError('Invalid route coordinate')
        x, y = point
        coordinates({'latitude': y, 'longitude': x})

    return {
        **context_status('routing', 'available', None),
        'distance_m': number(summary['distance'], 0),
        'duration_seconds': number(summary['duration'], 0),
        'origin': [lon, lat],
        'destination': [dest_lon, dest_lat],
        'profile': 'driving-car',
        'geometry': geometry,
        'attribution': (
            'openrouteservice / © OpenStreetMap contributors'
        ),
    }


async def fetch_context(name,event,previous=None,destination=None):
    """Failure-isolated bounded cache. Persisted event context also survives restarts."""
    prefix=CONTEXT_PREFIX.get(name,name)
    if not getattr(settings,prefix+'_enabled'):return context_status(name,reason='disabled')
    if event.get('is_demo'):return context_status(name,reason='demo_mode')
    if name=='routing' and not settings.openrouteservice_api_key.strip():return context_status(name,reason='not_configured')
    if name=='routing' and destination is None:return context_status(name,reason='destination_required')
    try:
        signature=context_signature(name,event,destination)
        key=(name,json.dumps(signature))
        cached=_context_cache.get(key)
        for packet in (previous,cached):
            if fresh_context(name,packet,signature):return deepcopy(packet)
        timeout=getattr(settings,prefix+'_timeout_seconds')
        if name in ('weather','air_quality'):call=_hourly_context(event,name)
        elif name=='location':call=_reverse_geocode(event)
        elif name=='eonet':call=_eonet_context(event)
        else:call=_route_context(event,destination)
        result=await asyncio.wait_for(call,timeout+1.2 if name=='location' else timeout)
        result['signature']=signature
        if result['status']=='available':
            _context_cache[key]=deepcopy(result); _context_cache.move_to_end(key)
            while len(_context_cache)>512:_context_cache.popitem(last=False)
            return result
    except (TimeoutError,httpx.TimeoutException):result=context_status(name,'failed','timeout')
    except httpx.HTTPError:result=context_status(name,'failed','provider_error')
    except (ValueError,KeyError,IndexError,TypeError,AttributeError):result=context_status(name,'failed','malformed_response')
    # Same-coordinate old evidence survives failed refresh, with its original timestamp.
    for packet in (previous,locals().get('cached')):
        if isinstance(packet,dict) and packet.get('status')=='available' and packet.get('signature')==locals().get('signature'):
            return {**deepcopy(packet),'refresh_status':result['status'],'refresh_reason':result['reason']}
    return result


async def fetch_weather_context(event,previous=None):return await fetch_context('weather',event,previous)
async def fetch_air_quality_context(event,previous=None):return await fetch_context('air_quality',event,previous)
async def reverse_geocode_event(event,previous=None):return await fetch_context('location',event,previous)
async def fetch_eonet_context(event,previous=None):return await fetch_context('eonet',event,previous)
async def fetch_route_context(event,destination=None,previous=None):return await fetch_context('routing',event,previous,destination)


async def enrich_external_context(events):
    # Missing context first, then newest and previously highest risk. Per-provider budgets.
    deadline=time.monotonic()+60
    for name in ('weather','air_quality','location','eonet'):
        prefix=CONTEXT_PREFIX.get(name,name); used=0
        ordered=sorted(events,key=lambda e:(not bool(e.get('context',{}).get(name,{}).get('status')=='available'),
                        e.get('last_seen_time',''),e.get('risk',{}).get('risk_score',0)),reverse=True)
        for event in ordered:
            context=event.setdefault('context',{}); previous=context.get(name)
            if not getattr(settings,prefix+'_enabled') or event.get('is_demo'):
                reason='demo_mode' if event.get('is_demo') else 'disabled'
                if not isinstance(previous,dict) or previous.get('reason')!=reason:
                    context[name]=context_status(name,reason=reason)
                continue
            try:fresh=fresh_context(name,previous,context_signature(name,event))
            except (ValueError,KeyError,TypeError):fresh=False
            if fresh:continue
            try:same_signature=isinstance(previous,dict) and previous.get('signature')==context_signature(name,event)
            except (ValueError,KeyError,TypeError):same_signature=False
            if used>=getattr(settings,prefix+'_events_per_sync') or time.monotonic()>=deadline:
                if same_signature and previous.get('status')=='available':
                    context[name]={**previous,'refresh_status':'deferred','refresh_reason':'per_sync_budget'}
                else:context[name]=context_status(name,'deferred','per_sync_budget')
                continue
            used+=1
            try:context[name]=await asyncio.wait_for(fetch_context(name,event,previous),max(0.01,deadline-time.monotonic()))
            except Exception:
                failure=context_status(name,'failed','provider_error')
                context[name]={**previous,'refresh_status':'failed','refresh_reason':'provider_error'} if same_signature and previous.get('status')=='available' else failure


    for event in events:
        context=event.setdefault('context',{})
        route=context.get('routing')
        if isinstance(route,dict) and route.get('status')=='available':
            try:unchanged=route.get('signature')==context_signature('routing',event,route.get('destination'))
            except (ValueError,KeyError,TypeError):unchanged=False
            if not unchanged:
                context['routing']=context_status('routing','deferred','event_changed')


def verified_context(event):
    result={}
    for name in CONTEXT_NAMES:
        packet=event.get('context',{}).get(name)
        try:matches=isinstance(packet,dict) and packet.get('signature')==context_signature(name,event,packet.get('destination'))
        except (ValueError,KeyError,TypeError):matches=False
        if matches and packet.get('status')=='available' and packet.get('version')==1:
            result[name]={key:deepcopy(packet[key]) for key in ('provider','fetched_at','status','refresh_status','refresh_reason',*CONTEXT_FIELDS[name]) if key in packet}
        else:result[name]='not available'
    return result


_firebase_app=None
_firebase_signature=None
_firebase_lock=threading.Lock()


def firebase_app():
    global _firebase_app,_firebase_signature
    if not settings.firebase_credentials_path:return None
    try:
        path=Path(settings.firebase_credentials_path).expanduser()
        if not path.is_absolute():path=Path(__file__).resolve().parents[2]/path
        if not path.is_file():return None
        signature=(str(path),path.stat().st_mtime_ns,settings.firebase_project_id)
        with _firebase_lock:
            if _firebase_app is not None and _firebase_signature==signature:return _firebase_app
            data=json.loads(path.read_text())
            project=settings.firebase_project_id or data.get('project_id')
            if not project or data.get('type')!='service_account' or data.get('project_id')!=project:return None
            import firebase_admin
            from firebase_admin import credentials
            credential=credentials.Certificate(data)
            if _firebase_app is not None:firebase_admin.delete_app(_firebase_app)
            _firebase_app=firebase_admin.initialize_app(credential,{'projectId':project,'httpTimeout':15},name='thermaguard-push')
            _firebase_signature=signature
            return _firebase_app
    except Exception:
        return None  # Never include paths, certificate contents, or provider exception text.


def send_push_notification(device_token,event):
    if not settings.push_notifications_enabled:return {'sent':False,'reason':'disabled'}
    if event.get('is_demo'):return {'sent':False,'reason':'demo_mode'}
    app=firebase_app()
    if app is None or not device_token:return {'sent':False,'reason':'not_configured'}
    try:
        from firebase_admin import messaging
        # Minimal lock-screen payload; authenticated dashboard provides sensitive evidence.
        message=messaging.Message(token=device_token,notification=messaging.Notification(
            title='ThermaGuard event alert',body='A thermal event meets your subscribed alert criteria. Open the dashboard to review.'),
            data={'event_id':event['id']})
        messaging.send(message,app=app)
        return {'sent':True,'reason':None}
    except Exception:
        return {'sent':False,'reason':'push_failed'}


def context_diagnostics():
    result={}
    for name in ('weather','air_quality','location','eonet','routing'):
        prefix=CONTEXT_PREFIX.get(name,name)
        result[name]='configured' if getattr(settings,prefix+'_enabled') else 'disabled'
        if name=='routing' and settings.routing_enabled and not settings.openrouteservice_api_key:result[name]='not_configured'
    result['firebase']=('configured' if firebase_app() is not None else 'not_configured') if settings.push_notifications_enabled else 'disabled'
    return result


# ============================================================
# PROVIDER HEALTH REGISTRY
#
# In-memory record of the last real interaction with each
# external provider: outcome, latency and timestamps. Never
# stores credentials, URLs with keys, or exception text — only
# safe category strings. Lives in the same process as the
# enrichment code so instrumentation cannot drift from reality.
# ============================================================

_HEALTH_LOCK = threading.Lock()
_HEALTH: dict = {}
_HEALTH_TTL_SECONDS = 7 * 86400
_SAFE_CATEGORIES = frozenset({
    'provider_error', 'request_failed', 'timeout', 'network_error',
    'malformed_response', 'unexpected_error', 'oauth_failed', 'push_failed',
    'osm_provider_unavailable', 'osm_request_failed',
})


def record_provider_call(name, outcome, latency_seconds=None, detail=None):
    """Record one real provider interaction. Never raises; never stores secret text.

    ``detail`` is accepted for call-site convenience but only a coarse,
    known-safe category string is ever persisted — raw exception text,
    headers, or key material can never leak into the status payload.
    """
    try:
        latency_ms = int(round(latency_seconds * 1000)) if isinstance(latency_seconds, (int, float)) \
            and math.isfinite(latency_seconds) else None
        category = str(detail) if detail and str(detail) in _SAFE_CATEGORIES else None
        now = utc_now().isoformat()
        with _HEALTH_LOCK:
            entry = _HEALTH.setdefault(name, {})
            if outcome == 'success':
                entry.update(last_success=now, last_latency_ms=latency_ms,
                             last_error_category=None, last_error_at=None)
            elif outcome in ('failure', 'disabled', 'not_configured'):
                entry.update(last_attempt=now, last_latency_ms=latency_ms)
                if outcome == 'failure':
                    entry.update(last_error_category=category or 'provider_error',
                                 last_error_at=now)
            entry['last_activity_at'] = now
    except Exception:
        pass  # Health bookkeeping must never affect the calling code path.


def _fresh_health(entry):
    if not isinstance(entry, dict) or not entry:
        return None
    return entry


def provider_health():
    """Safe status snapshot for the status UI: config + last real interaction.

    Values: healthy (enabled, recent success), configured (enabled, no
    call recorded yet), degraded (enabled, recent success but later
    failure), failed (enabled, last attempt failed), disabled,
    not_configured. No secrets, keys, or URLs are ever included.
    """
    with _HEALTH_LOCK:
        observed = {name: dict(entry) for name, entry in _HEALTH.items() if isinstance(entry, dict)}
    result = dict(context_diagnostics())
    # FIRMS configuration mirrors the /firms/status definition.
    result['firms'] = 'configured' if settings.firms_map_key else 'not_configured'
    result['gemini'] = 'configured' if settings.gemini_configured else \
        ('disabled' if not settings.gemini_enabled else 'not_configured')
    result['smtp'] = 'configured' if settings.smtp_configured else \
        ('disabled' if not settings.smtp_enabled else 'not_configured')
    for name, entry in observed.items():
        if name not in result:
            # Registry-only providers (osm, copernicus) have no config flag;
            # their status comes from observed interactions alone.
            if entry.get('last_error_category'):
                result[name] = 'degraded' if entry.get('last_success') else 'failed'
            elif entry.get('last_success'):
                result[name] = 'healthy'
            continue
        state = result.get(name)
        if state in (None, 'disabled', 'not_configured'):
            continue
        if entry.get('last_error_category'):
            result[name] = 'degraded' if entry.get('last_success') else 'failed'
        elif entry.get('last_success'):
            result[name] = 'healthy'
    return {
        'providers': {
            name: {
                'status': state,
                'last_success': observed.get(name, {}).get('last_success'),
                'last_failure': observed.get(name, {}).get('last_error_at'),
                'last_error_category': observed.get(name, {}).get('last_error_category'),
                'last_latency_ms': observed.get(name, {}).get('last_latency_ms'),
            }
            for name, state in result.items()
        },
        'note': 'Configuration and last real interaction; diagnostics endpoints probe providers live.',
    }


async def _timed(coro):
    """Await a coroutine while measuring its wall-clock latency in seconds."""
    started = time.monotonic()
    try:
        return await coro, (time.monotonic() - started), None
    except Exception as exc:
        return None, (time.monotonic() - started), exc


async def firms_sources():
    """Instrumented FIRMS availability check (registry wrapper; see _firms_sources_impl)."""
    if not settings.firms_map_key:
        record_provider_call('firms', 'not_configured')
        raise ValueError('FIRMS credentials unavailable')
    result, latency, exc = await _timed(_firms_sources_impl())
    if exc is None:
        record_provider_call('firms', 'success', latency)
        return result
    record_provider_call('firms', 'failure', latency, _safe_category(exc))
    raise exc


async def osm(event):
    """Instrumented OSM/Overpass context (registry wrapper; see _osm_request)."""
    result, latency, exc = await _timed(_osm_request(event))
    if exc is None:
        record_provider_call('osm', 'success' if result.get('osm_context_available') else 'failure',
                             latency, None if result.get('osm_context_available') else str(result.get('osm_reason') or 'osm_unavailable')[:60])
        return result
    record_provider_call('osm', 'failure', latency, _safe_category(exc))
    raise exc


async def satellite(event=None):
    """Instrumented Copernicus context (registry wrapper; see _satellite_request)."""
    result, latency, exc = await _timed(_satellite_request(event))
    if exc is None:
        record_provider_call('copernicus', 'success' if result.get('satellite_context_available') else 'failure',
                             latency, None if result.get('satellite_context_available') else str(result.get('reason') or 'unavailable')[:60])
        return result
    record_provider_call('copernicus', 'failure', latency, _safe_category(exc))
    raise exc


def _safe_category(exc):
    """Coarse, secret-free failure category for an exception object."""
    try:
        import httpx as _httpx
        if isinstance(exc, _httpx.HTTPStatusError):
            code = getattr(getattr(exc, 'response', None), 'status_code', None)
            return 'provider_error' if (isinstance(code, int) and code >= 500) else 'request_failed'
        if isinstance(exc, (_httpx.TimeoutException, TimeoutError)):
            return 'timeout'
        if isinstance(exc, _httpx.HTTPError):
            return 'network_error'
    except Exception:
        pass
    name = type(exc).__name__
    return {'ValueError': 'malformed_response', 'KeyError': 'malformed_response',
            'TypeError': 'malformed_response', 'IndexError': 'malformed_response'}.get(name, 'unexpected_error')


async def eonet_active_events():
    """Current open NASA EONET natural-hazard events, for the map hazard layer.

    Read-only supporting context, never classification evidence: only
    open events with Point geometry are listed; unparseable entries are
    skipped, and the endpoint reports unavailable on any failure.
    """
    if not settings.eonet_enabled:
        return {'available': False, 'reason': 'disabled', 'events': []}
    try:
        started = time.monotonic()
        params = dict(status='open', limit=60, days=20)
        data = await _context_json(settings.eonet_api_url, params,
                                   settings.eonet_timeout_seconds, provider='eonet')
        if not isinstance(data, dict) or not isinstance(data.get('events'), list):
            raise ValueError('Invalid EONET response')
        events = []
        for item in data['events']:
            if not isinstance(item, dict):
                continue
            geometries = item.get('geometry') or []
            point = next((g for g in reversed(geometries)
                          if isinstance(g, dict) and g.get('type') == 'Point'), None)
            if point is None:
                continue  # Unsupported shapes are never approximated as points.
            xy = point.get('coordinates')
            if not isinstance(xy, (list, tuple)) or len(xy) < 2:
                continue
            lon, lat = xy[0], xy[1]
            try:
                coordinates({'latitude': lat, 'longitude': lon})
            except (ValueError, KeyError, TypeError):
                continue
            categories = item.get('categories', [])
            events.append({
                'eonet_id': str(item.get('id') or ''),
                'title': str(item.get('title') or '')[:200],
                'category': ', '.join(c['title'] for c in categories if isinstance(c, dict) and isinstance(c.get('title'), str))[:100],
                'latitude': lat,
                'longitude': lon,
                'event_date': str(point.get('date') or ''),
                'source': 'NASA EONET',
            })
        record_provider_call('eonet', 'success', time.monotonic() - started)
        return {'available': True, 'reason': None, 'count': len(events), 'events': events[:40]}
    except Exception as exc:
        category = _safe_category(exc)
        record_provider_call('eonet', 'failure', None, category)
        return {'available': False, 'reason': category, 'events': []}
