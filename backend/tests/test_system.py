import os

# IMPORTANT:
# Tests require deterministic demo fixtures.
# Must be set before importing app.config / app.main.
os.environ["DEMO_MODE"] = "true"

import asyncio
import csv
from pathlib import Path

import pytest
import httpx

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main, ml, providers
from app.config import REQUIRED_RISK_WEIGHT_KEYS
from app.database import (
    Base,
    get_db,
    Detection,
    Event,
    Organization,
    AreaAssignment,
    User,
    Alert,
)
from app.intelligence import (
    validate,
    cluster,
    features,
    assess,
    FEATURES,
)
from app.security import hash_password


# ============================================================
# TEST DATABASE / CLIENT
# ============================================================

@pytest.fixture
def client(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={
            "check_same_thread": False
        },
        poolclass=StaticPool,
    )

    factory = sessionmaker(
        engine,
        expire_on_commit=False,
    )

    monkeypatch.setattr(
        main,
        "engine",
        engine,
    )

    monkeypatch.setattr(
        main,
        "Session",
        factory,
    )

    def db():
        with factory() as session:
            yield session

    main.app.dependency_overrides[
        get_db
    ] = db

    with TestClient(
        main.app
    ) as test_client:
        yield (
            test_client,
            factory,
        )

    main.app.dependency_overrides.clear()


# ============================================================
# AUTH HELPER
# ============================================================

def auth(
    client,
    operator=False,
):
    email = (
        "operator"
        if operator
        else "admin"
    )

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email":
                (
                    f"{email}"
                    "@demo.thermaguard.local"
                ),
            "password":
                "DemoTherma2026!",
        },
    )

    assert (
        response.status_code
        == 200
    )

    return {
        "Authorization":
            (
                "Bearer "
                + response.json()[
                    "access_token"
                ]
            )
    }


# ============================================================
# FIRMS SAMPLE ROW
# ============================================================

def row(**kwargs):
    return dict(
        latitude="22",
        longitude="70",
        acq_date="2026-09-10",
        acq_time="0100",
        frp="100",
        bright_ti4="340",
        satellite="test",
        instrument="VIIRS",
        **kwargs,
    )


# ============================================================
# VALIDATION
# ============================================================

def test_validation():
    source = row()

    result = validate(
        source
    )

    assert (
        result["raw"]
        == source
    )

    assert (
        not result["is_demo"]
    )

    assert (
        result["source"]
        == "NASA FIRMS"
    )

    invalid_values = [
        (
            "latitude",
            "91",
        ),
        (
            "longitude",
            "nan",
        ),
        (
            "frp",
            "-1",
        ),
        (
            "acq_time",
            "9999",
        ),
    ]

    for (
        key,
        value,
    ) in invalid_values:

        with pytest.raises(
            ValueError
        ):
            validate(
                {
                    **source,
                    key: value,
                }
            )


# ============================================================
# EVENT CLUSTERING
# ============================================================

def test_clustering_and_isolation():
    a = validate(
        row()
    )

    b = validate(
        {
            **row(),
            "latitude":
                "22.001",
            "acq_time":
                "0200",
        }
    )

    # Duplicate observation ignored.
    assert (
        len(
            cluster(
                [
                    a,
                    b,
                    a,
                ]
            )
        )
        == 1
    )

    # Clustering deterministic.
    assert (
        cluster(
            [
                b,
                a,
            ]
        )[0]["id"]
        ==
        cluster(
            [
                a,
                b,
            ]
        )[0]["id"]
    )

    # Demo and real observations
    # must never cluster together.
    assert (
        len(
            cluster(
                [
                    a,
                    validate(
                        row(),
                        True,
                    ),
                ]
            )
        )
        == 2
    )

    # Observations outside time window
    # remain separate.
    assert (
        len(
            cluster(
                [
                    a,
                    validate(
                        {
                            **row(),
                            "acq_date":
                                "2026-09-12",
                        }
                    ),
                ]
            )
        )
        == 2
    )


# ============================================================
# FEATURES / RISK / HISTORICAL BASELINE
# ============================================================

def test_features_risk_baseline():
    event = cluster(
        [
            validate(
                row()
            )
        ]
    )[0]

    assert (
        len(
            features(
                event
            )
        )
        == len(
            FEATURES
        )
    )

    # --------------------------------------------------------
    # No history
    # --------------------------------------------------------

    risk = assess(
        event,
        [],
    )

    assert (
        risk["risk_score"]
        == 36
    )

    assert (
        risk[
            "abnormality"
        ][
            "baseline_available"
        ]
        is False
    )

    assert (
        risk[
            "abnormality"
        ][
            "abnormality_status"
        ]
        == "unavailable"
    )

    # --------------------------------------------------------
    # One historical event is deliberately insufficient
    # --------------------------------------------------------

    past = {
        **event,

        "id":
            "TG-history-one",

        "start_time":
            "2026-09-01T00:00:00+00:00",

        "last_seen_time":
            "2026-09-01T01:00:00+00:00",

        "mean_frp":
            20.0,

        "max_frp":
            20.0,
    }

    risk = assess(
        event,
        [
            past
        ],
    )

    assert (
        risk[
            "abnormality"
        ][
            "baseline_available"
        ]
        is False
    )

    assert (
        risk[
            "abnormality"
        ][
            "abnormality_status"
        ]
        == "unavailable"
    )

    # --------------------------------------------------------
    # Five legitimate historical events establish baseline
    # --------------------------------------------------------

    historical = []

    for i in range(5):

        historical.append(
            {
                **event,

                "id":
                    (
                        f"TG-history-{i}"
                    ),

                "start_time":
                    (
                        f"2026-09-0"
                        f"{i + 1}"
                        "T00:00:00+00:00"
                    ),

                "last_seen_time":
                    (
                        f"2026-09-0"
                        f"{i + 1}"
                        "T01:00:00+00:00"
                    ),

                "mean_frp":
                    10.0,

                "max_frp":
                    12.0,

                "mean_brightness":
                    300.0,

                "spatial_spread_km":
                    0.2,

                "duration_hours":
                    1.0,

                "detection_count":
                    1,
            }
        )

    risk = assess(
        event,
        historical,
    )

    assert (
        risk[
            "abnormality"
        ][
            "baseline_available"
        ]
        is True
    )

    assert (
        risk[
            "abnormality"
        ][
            "abnormality_score"
        ]
        is not None
    )

    assert (
        risk[
            "abnormality"
        ][
            "explanation_features"
        ][
            "historical_event_count"
        ]
        == 5
    )


# ============================================================
# HEALTH / AUTH / MODEL GATE
# ============================================================

def test_health_login_model_gate(
    client,
):
    c, _ = client

    assert (
        c.get(
            "/health"
        ).json()[
            "status"
        ]
        == "ok"
    )

    assert (
        c.get(
            "/api/v1/events"
        ).status_code
        == 401
    )

    headers = auth(
        c
    )

    model_status = (
        c.get(
            "/api/v1/model/status",
            headers=headers,
        )
        .json()
    )

    assert (
        model_status[
            "training_ready"
        ]
        is False
    )

    assert (
        c.post(
            "/api/v1/model/train",
            headers=headers,
        ).status_code
        == 409
    )

    assert (
        c.post(
            "/api/v1/auth/login",
            json={
                "email":
                    (
                        "admin@demo."
                        "thermaguard.local"
                    ),
                "password":
                    "wrongpassword123",
            },
        ).status_code
        == 401
    )


# ============================================================
# PIPELINE / EVIDENCE / ALERTS
# ============================================================

def test_pipeline_evidence_alerts(
    client,
):
    c, factory = client

    headers = auth(
        c
    )

    events = c.get(
        "/api/v1/events",
        headers=headers,
    ).json()

    assert (
        len(events)
        == 4
    )

    first = events[0]

    assert (
        first["is_demo"]
    )

    assert (
        first[
            "classification"
        ][
            "classification_confidence"
        ]
        is None
    )

    evidence = c.get(
        (
            f"/api/v1/events/"
            f"{first['id']}/evidence"
        ),
        headers=headers,
    ).json()

    assert (
        len(
            evidence[
                "detected_facts"
            ]
        )
        == 3
    )

    assert (
        evidence[
            "risk_assessment"
        ][
            "risk_score"
        ]
        == 60
    )

    alerts = c.get(
        "/api/v1/alerts",
        headers=headers,
    ).json()

    assert (
        len(alerts)
        == 1
    )

    result = c.post(
        (
            f"/api/v1/alerts/"
            f"{alerts[0]['id']}"
            "/acknowledge"
        ),
        headers=headers,
    ).json()

    assert (
        result["status"]
        == "acknowledged"
    )

    # Duplicate alert must not be created.
    with factory() as db:

        main.create_alerts(
            db,
            first,
        )

        db.commit()

        assert (
            len(
                list(
                    db.scalars(
                        select(
                            Alert
                        )
                    )
                )
            )
            == 1
        )


# ============================================================
# ORGANIZATION SCOPE
# ============================================================

def test_organization_scope(
    client,
):
    c, _ = client

    admin = auth(
        c
    )

    operator = auth(
        c,
        True,
    )

    all_events = c.get(
        "/api/v1/events",
        headers=admin,
    ).json()

    events = c.get(
        "/api/v1/events",
        headers=operator,
    ).json()

    assert (
        len(events)
        == 2
    )

    hidden = next(
        event
        for event in all_events
        if event not in events
    )

    for suffix in [
        "",
        "/evidence",
        "/risk",
        "/history",
    ]:

        assert (
            c.get(
                (
                    "/api/v1/events/"
                    + hidden["id"]
                    + suffix
                ),
                headers=operator,
            ).status_code
            == 404
        )

    assert (
        c.get(
            "/api/v1/admin/organizations",
            headers=operator,
        ).status_code
        == 403
    )

    assert (
        c.post(
            "/api/v1/firms/sync",
            headers=operator,
            json={},
        ).status_code
        == 403
    )

    assert (
        c.post(
            "/api/v1/copilot/chat",
            headers=operator,
            json={
                "question":
                    "Explain",
                "event_id":
                    hidden["id"],
            },
        ).status_code
        == 404
    )


# ============================================================
# REGISTRATION PRIVILEGE ESCALATION
# ============================================================

def test_registration_cannot_escalate(
    client,
):
    c, _ = client

    c.post(
        "/api/v1/auth/register",
        json={
            "email":
                "new@example.invalid",

            "password":
                "longsecurepassword",

            "role":
                "admin",

            "organization_id":
                1,
        },
    )

    result = c.post(
        "/api/v1/auth/login",
        json={
            "email":
                "new@example.invalid",

            "password":
                "longsecurepassword",
        },
    ).json()

    headers = {
        "Authorization":
            (
                "Bearer "
                + result[
                    "access_token"
                ]
            )
    }

    assert (
        c.get(
            "/api/v1/events",
            headers=headers,
        ).json()
        == []
    )

    assert (
        c.get(
            "/api/v1/auth/me",
            headers=headers,
        ).json()[
            "role"
        ]
        == "organization"
    )


# ============================================================
# DEMO SYNC / COPILOT FALLBACK
# ============================================================

def test_demo_sync_and_fallback(
    client,
    monkeypatch,
):
    c, _ = client

    headers = auth(
        c
    )

    assert (
        c.post(
            "/api/v1/firms/sync",
            headers=headers,
            json={},
        ).status_code
        == 409
    )

    response = c.post(
        "/api/v1/copilot/chat",
        headers=headers,
        json={
            "question":
                "Why is the event risky?"
        },
    )

    assert (
        response.json()[
            "mode"
        ]
        == "deterministic_fallback"
    )

    assert (
        "DEMO DATA"
        in response.json()[
            "answer"
        ]
    )


# ============================================================
# FIRMS PROVIDER MOCK
# ============================================================

def test_firms_mock(
    monkeypatch,
):
    monkeypatch.setattr(
        main.settings,
        "firms_map_key",
        "test",
    )

    original = (
        httpx.AsyncClient
    )

    def handler(request):

        return httpx.Response(
            200,
            text=(
                "latitude,longitude,"
                "acq_date,acq_time,"
                "frp,bright_ti4\n"
                "22,70,2026-09-10,"
                "0100,100,340\n"
                "999,70,2026-09-10,"
                "0100,100,340"
            ),
        )

    monkeypatch.setattr(
        providers.httpx,
        "AsyncClient",
        lambda **kwargs:
            original(
                transport=httpx.MockTransport(
                    handler
                ),
                **kwargs,
            ),
    )

    records, rejected = (
        asyncio.run(
            providers.firms(
                [
                    68,
                    6,
                    98,
                    38,
                ]
            )
        )
    )

    assert (
        len(records)
        == 1
    )

    assert (
        rejected
        == 1
    )

    assert (
        not records[0][
            "is_demo"
        ]
    )


# ============================================================
# OSM MOCK
# ============================================================

def test_osm_mock_and_failure(
    monkeypatch,
):
    original = (
        httpx.AsyncClient
    )

    def handler(request):

        return httpx.Response(
            200,
            json={
                "elements": [
                    {
                        "type":
                            "node",

                        "id":
                            1,

                        "lat":
                            22,

                        "lon":
                            70,

                        "tags": {
                            "landuse":
                                "industrial"
                        },
                    }
                ]
            },
        )

    monkeypatch.setattr(
        providers.httpx,
        "AsyncClient",
        lambda **kwargs:
            original(
                transport=httpx.MockTransport(
                    handler
                ),
                **kwargs,
            ),
    )

    result = asyncio.run(
        providers.osm(
            {
                "latitude": 22,
                "longitude": 70,
            }
        )
    )

    assert (
        result[
            "osm_context_available"
        ]
    )

    assert (
        result[
            "distance_to_industrial_m"
        ]
        == 0
    )

    assert (
        result[
            "distance_to_forest_m"
        ]
        is None
    )

    def failure(request):
        return httpx.Response(
            503
        )

    monkeypatch.setattr(
        providers.httpx,
        "AsyncClient",
        lambda **kwargs:
            original(
                transport=httpx.MockTransport(
                    failure
                ),
                **kwargs,
            ),
    )

    result = asyncio.run(
        providers.osm(
            {
                "latitude": 22,
                "longitude": 70,
            }
        )
    )

    assert (
        not result[
            "osm_context_available"
        ]
    )


# ============================================================
# TRAINING MUST EXCLUDE DEMO DATA
# ============================================================

def test_training_excludes_demo(
    tmp_path,
    monkeypatch,
):
    path = (
        tmp_path
        / "labels.csv"
    )

    monkeypatch.setattr(
        ml,
        "DATA",
        path,
    )

    path.write_text(
        (
            "event_id,split_group,"
            "label,reviewed,reviewer,"
            "source_reference,is_demo,"
            "mean_frp\n"
            "e1,g1,industrial_fire,"
            "true,reviewer,test,true,100\n"
        )
    )

    assert (
        ml.dataset()
        == []
    )

    assert (
        not ml.status()[
            "training_ready"
        ]
    )


# ============================================================
# ADMIN THRESHOLD / BOUNDS
# ============================================================

def test_threshold_and_admin_bounds(
    client,
):
    c, _ = client

    headers = auth(
        c
    )

    operator = auth(
        c,
        True,
    )

    assert (
        c.post(
            "/api/v1/admin/threshold",
            headers=operator,
            json={
                "threshold": 20
            },
        ).status_code
        == 403
    )

    assert (
        c.post(
            "/api/v1/admin/threshold",
            headers=headers,
            json={
                "threshold": 101
            },
        ).status_code
        == 422
    )

    result = c.post(
        "/api/v1/admin/threshold",
        headers=headers,
        json={
            "threshold": 50
        },
    ).json()

    assert (
        result[
            "threshold"
        ]
        == 50
    )

    assert (
        c.get(
            "/api/v1/admin/threshold",
            headers=headers,
        ).json()[
            "threshold"
        ]
        == 50
    )

    assert (
        c.post(
            "/api/v1/admin/assignments",
            headers=headers,
            json={
                "organization_id":
                    1,

                "area_name":
                    "Invalid",

                "bounds":
                    [
                        90,
                        20,
                        70,
                        30,
                    ],
            },
        ).status_code
        == 422
    )


# ============================================================
# REAL SYNC ROUTE WITH MOCKED EXTERNAL PROVIDERS
# ============================================================

def test_real_sync_route_mocked(
    client,
    monkeypatch,
):
    c, factory = client

    with factory() as db:

        db.add(
            User(
                email=(
                    "real-admin@"
                    "example.invalid"
                ),
                password=hash_password(
                    "realpassword123"
                ),
                role="admin",
            )
        )

        db.commit()

    token = c.post(
        "/api/v1/auth/login",
        json={
            "email":
                (
                    "real-admin@"
                    "example.invalid"
                ),
            "password":
                "realpassword123",
        },
    ).json()[
        "access_token"
    ]

    headers = {
        "Authorization":
            "Bearer " + token
    }

    monkeypatch.setattr(
        main.settings,
        "demo_mode",
        False,
    )

    async def fake_firms(
        bounds,
        days,
    ):
        return [
            validate(
                row()
            )
        ], 0

    async def fake_osm(
        event,
    ):
        return {
            "osm_context_available":
                False
        }

    monkeypatch.setattr(
        providers,
        "firms",
        fake_firms,
    )

    monkeypatch.setattr(
        providers,
        "osm",
        fake_osm,
    )

    result = c.post(
        "/api/v1/firms/sync",
        headers=headers,
        json={},
    )

    assert (
        result.status_code
        == 200
    )

    assert (
        result.json()[
            "events"
        ]
        == 1
    )

    assert (
        len(
            c.get(
                "/api/v1/events",
                headers=headers,
            ).json()
        )
        == 1
    )

    # Demo account must not work
    # while application is switched
    # to real mode.
    assert (
        c.post(
            "/api/v1/auth/login",
            json={
                "email":
                    (
                        "admin@demo."
                        "thermaguard.local"
                    ),
                "password":
                    "DemoTherma2026!",
            },
        ).status_code
        == 401
    )

    assert (
        c.post(
            "/api/v1/firms/sync",
            headers=headers,
            json={},
        ).json()[
            "events"
        ]
        == 1
    )

    with factory() as db:

        detections = list(
            db.scalars(
                select(
                    Detection
                ).where(
                    Detection.is_demo
                    == False
                )
            )
        )

        assert (
            len(detections)
            == 1
        )


# ============================================================
# OLLAMA FAILURE MUST NOT REMOVE EVENTS
# ============================================================

def test_ollama_down_retains_events(
    client,
    monkeypatch,
):
    c, _ = client

    headers = auth(
        c
    )

    monkeypatch.setattr(
        main.settings,
        "ollama_enabled",
        True,
    )

    monkeypatch.setattr(
        main.settings,
        "ollama_model",
        "test",
    )

    original = (
        httpx.AsyncClient
    )

    def failure(request):
        return httpx.Response(
            503
        )

    monkeypatch.setattr(
        main.httpx,
        "AsyncClient",
        lambda **kwargs:
            original(
                transport=httpx.MockTransport(
                    failure
                ),
                **kwargs,
            ),
    )

    result = c.post(
        "/api/v1/copilot/chat",
        headers=headers,
        json={
            "question":
                "Explain"
        },
    ).json()

    assert (
        result["mode"]
        == "deterministic_fallback"
    )

    assert (
        len(
            c.get(
                "/api/v1/events",
                headers=headers,
            ).json()
        )
        == 4
    )


# ============================================================
# EVENT ID CHANGE PRESERVES ALERT ACKNOWLEDGEMENT
# ============================================================

def test_cluster_identity_change_preserves_acknowledgement(
    client,
):
    c, factory = client

    headers = auth(
        c
    )

    alert = c.get(
        "/api/v1/alerts",
        headers=headers,
    ).json()[0]

    c.post(
        (
            f"/api/v1/alerts/"
            f"{alert['id']}"
            "/acknowledge"
        ),
        headers=headers,
    )

    earlier = validate(
        {
            **row(),

            "latitude":
                "22.30",

            "longitude":
                "70.80",

            "acq_date":
                "2026-09-09",

            "acq_time":
                "2300",
        },
        True,
    )

    with factory() as db:

        asyncio.run(
            main.process(
                db,
                [
                    earlier
                ],
                False,
            )
        )

    updated = c.get(
        "/api/v1/alerts",
        headers=headers,
    ).json()

    assert (
        len(updated)
        == 1
    )

    assert (
        updated[0][
            "status"
        ]
        == "acknowledged"
    )

    assert (
        updated[0][
            "event_id"
        ]
        != alert[
            "event_id"
        ]
    )

    assert (
        c.get(
            (
                "/api/v1/events/"
                + updated[0][
                    "event_id"
                ]
            ),
            headers=headers,
        ).status_code
        == 200
    )


# ============================================================
# RISK WEIGHTS
# ============================================================

def test_risk_weights_total_100():
    from app.config import settings

    assert (
        set(
            settings.risk_weights
        )
        ==
        set(
            REQUIRED_RISK_WEIGHT_KEYS
        )
    )

    assert all(
        value >= 0
        for value
        in settings.risk_weights.values()
    )

    assert (
        round(
            sum(
                settings.risk_weights.values()
            ),
            6,
        )
        == 100
    )


def test_risk_weight_validation_rejects_invalid():
    from app.config import Settings

    complete = {
        "thermal_severity":
            50,

        "persistence":
            10,

        "industrial_proximity":
            10,

        "residential_proximity":
            10,

        "infrastructure_exposure":
            5,

        "classification_context":
            5,

        "historical_abnormality":
            10,
    }

    base = {
        "database_url":
            "sqlite://",

        "jwt_secret":
            "x" * 32,

        "demo_mode":
            "true",
    }

    with pytest.raises(
        Exception
    ):
        Settings(
            **{
                **base,
                "risk_weights": {
                    **complete,
                    "thermal_severity":
                        110,
                },
            }
        )

    with pytest.raises(
        Exception
    ):
        Settings(
            **{
                **base,
                "risk_weights": {
                    **complete,
                    "thermal_severity":
                        -10,
                },
            }
        )

    with pytest.raises(
        Exception
    ):
        Settings(
            **{
                **base,
                "risk_weights": {
                    **complete,
                    "bogus_extra":
                        5,
                },
            }
        )

    with pytest.raises(
        Exception
    ):
        Settings(
            **{
                **base,
                "risk_weights": {
                    key: 10
                    for key
                    in REQUIRED_RISK_WEIGHT_KEYS
                },
            }
        )

    valid = Settings(
        **{
            **base,
            "risk_weights":
                complete,
        }
    )

    assert (
        round(
            sum(
                valid
                .risk_weights
                .values()
            ),
            6,
        )
        == 100
    )


# ============================================================
# COPERNICUS CREDENTIALS MISSING
# ============================================================

def test_satellite_credentials_missing(
    monkeypatch,
):
    monkeypatch.setattr(
        providers.settings,
        "copernicus_client_id",
        "",
    )

    result = asyncio.run(
        providers.satellite(
            {
                "latitude":
                    22,

                "longitude":
                    70,

                "last_seen_time":
                    (
                        "2026-09-10"
                        "T01:00:00+00:00"
                    ),
            }
        )
    )

    assert (
        result[
            "satellite_context_available"
        ]
        is False
    )

    assert (
        result["reason"]
        == "credentials_missing"
    )

    assert (
        result["ndvi"]
        is None
    )


# ============================================================
# COPERNICUS SUCCESS + PROVIDER FAILURE
# ============================================================

def test_satellite_success_mock(
    monkeypatch,
):
    monkeypatch.setattr(
        providers.settings,
        "copernicus_client_id",
        "cid",
    )

    monkeypatch.setattr(
        providers.settings,
        "copernicus_client_secret",
        "secret",
    )

    monkeypatch.setattr(
        providers.settings,
        "satellite_provider",
        "copernicus",
    )

    original = (
        httpx.AsyncClient
    )

    providers._token_cache.clear()

    def handler(request):

        if (
            request.url.host
            ==
            "identity.dataspace.copernicus.eu"
        ):

            return httpx.Response(
                200,
                json={
                    "access_token":
                        "tok",

                    "expires_in":
                        300,
                },
            )

        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "interval": {
                            "from":
                                (
                                    "2026-09-10"
                                    "T00:00:00Z"
                                ),

                            "to":
                                (
                                    "2026-09-11"
                                    "T00:00:00Z"
                                ),
                        },

                        "outputs": {
                            "ndvi": {
                                "bands": {
                                    "B0": {
                                        "stats": {
                                            "mean":
                                                0.41232,

                                            "sampleCount":
                                                3036,

                                            "noDataCount":
                                                0,
                                        }
                                    }
                                }
                            }
                        },
                    }
                ],

                "status":
                    "OK",
            },
        )

    monkeypatch.setattr(
        providers.httpx,
        "AsyncClient",
        lambda **kwargs:
            original(
                transport=httpx.MockTransport(
                    handler
                ),
                **kwargs,
            ),
    )

    result = asyncio.run(
        providers.satellite(
            {
                "latitude":
                    22,

                "longitude":
                    70,

                "last_seen_time":
                    (
                        "2026-09-10"
                        "T01:00:00+00:00"
                    ),
            }
        )
    )

    assert (
        result[
            "satellite_context_available"
        ]
        is True
    )

    assert (
        result["ndvi"]
        == 0.4123
    )

    assert (
        result[
            "acquisition_date"
        ]
        == "2026-09-10"
    )

    assert (
        result["reason"]
        is None
    )

    # --------------------------------------------------------
    # Provider 503 -> provider_unavailable
    # --------------------------------------------------------

    def failure(request):
        return httpx.Response(
            503
        )

    monkeypatch.setattr(
        providers.httpx,
        "AsyncClient",
        lambda **kwargs:
            original(
                transport=httpx.MockTransport(
                    failure
                ),
                **kwargs,
            ),
    )

    result = asyncio.run(
        providers.satellite(
            {
                "latitude":
                    22,

                "longitude":
                    70,

                "last_seen_time":
                    (
                        "2026-09-10"
                        "T01:00:00+00:00"
                    ),
            }
        )
    )

    assert (
        result[
            "satellite_context_available"
        ]
        is False
    )

    assert (
        result["reason"]
        == "provider_unavailable"
    )


# ============================================================
# SATELLITE FEATURE PROPAGATION
# ============================================================

def test_satellite_feature_propagation(
    monkeypatch,
):
    monkeypatch.setattr(
        providers.settings,
        "copernicus_client_id",
        "",
    )

    event = cluster(
        [
            validate(
                row()
            )
        ]
    )[0]

    context = asyncio.run(
        providers.satellite(
            event
        )
    )

    event[
        "context"
    ] = context

    assert (
        len(
            features(
                event
            )
        )
        == len(
            FEATURES
        )
    )

    risk = assess(
        event,
        [],
    )

    assert (
        risk[
            "missing_context"
        ]
    )

    assert (
        "ndvi"
        in risk[
            "missing_context"
        ]
    )


# ============================================================
# DEMO SATELLITE MUST BE BLOCKED
# ============================================================

def test_demo_satellite_blocked(
    client,
    monkeypatch,
):
    c, factory = client

    headers = auth(
        c
    )

    events = c.get(
        "/api/v1/events",
        headers=headers,
    ).json()

    for event in events:

        assert (
            event[
                "context"
            ][
                "satellite_context_available"
            ]
            is False
        )

        assert (
            event[
                "context"
            ][
                "reason"
            ]
            == "demo_mode"
        )

        assert (
            event[
                "context"
            ][
                "ndvi"
            ]
            is None
        )

    demo_threshold = (
        c.get(
            "/api/v1/admin/threshold",
            headers=headers,
        )
        .json()[
            "threshold"
        ]
    )

    assert (
        demo_threshold
        == 60
    )


# ============================================================
# ANALYTICS INSUFFICIENT HISTORY
# ============================================================

def test_analytics_insufficient_history(
    client,
    monkeypatch,
):
    from app import security

    c, factory = client

    with factory() as db:

        db.add(
            User(
                email=(
                    "hist-admin@"
                    "example.invalid"
                ),

                password=hash_password(
                    "histpassword123"
                ),

                role=
                    "admin",
            )
        )

        db.commit()

    token = (
        c.post(
            "/api/v1/auth/login",
            json={
                "email":
                    (
                        "hist-admin@"
                        "example.invalid"
                    ),

                "password":
                    "histpassword123",
            },
        )
        .json()[
            "access_token"
        ]
    )

    headers = {
        "Authorization":
            "Bearer " + token
    }

    monkeypatch.setattr(
        main.settings,
        "demo_mode",
        False,
    )

    assert (
        c.get(
            (
                "/api/v1/analytics/"
                "summary?days=365"
            ),
            headers=headers,
        ).json()
        ==
        {
            "available":
                False,

            "reason":
                "insufficient_history",

            "window_days":
                365,

            "is_demo":
                False,
        }
    )

    assert (
        c.get(
            (
                "/api/v1/analytics/"
                "trends?days=365"
            ),
            headers=headers,
        ).json()
        ==
        {
            "available":
                False,

            "reason":
                "insufficient_history",

            "window_days":
                365,

            "is_demo":
                False,
        }
    )

    assert (
        c.get(
            (
                "/api/v1/analytics/"
                "trends?days=366"
            ),
            headers=headers,
        ).status_code
        == 422
    )

    security._login_failures.clear()


# ============================================================
# LOGIN THROTTLING
# ============================================================

def test_login_throttling(
    client,
    monkeypatch,
):
    from app import security

    monkeypatch.setattr(
        security,
        "_login_failures",
        security.defaultdict(
            list
        ),
    )

    c, _ = client

    for _ in range(10):

        assert (
            c.post(
                "/api/v1/auth/login",
                json={
                    "email":
                        (
                            "admin@demo."
                            "thermaguard.local"
                        ),

                    "password":
                        "wrongpassword123",
                },
            ).status_code
            == 401
        )

    assert (
        c.post(
            "/api/v1/auth/login",
            json={
                "email":
                    (
                        "admin@demo."
                        "thermaguard.local"
                    ),

                "password":
                    "wrongpassword123",
            },
        ).status_code
        == 429
    )

    # Throttling one email must not
    # block a different account.
    assert (
        c.post(
            "/api/v1/auth/login",
            json={
                "email":
                    (
                        "operator@demo."
                        "thermaguard.local"
                    ),

                "password":
                    "DemoTherma2026!",
            },
        ).status_code
        == 200
    )# ============================================================
# REVIEW-AND-LABEL WORKFLOW
# ============================================================

REVIEW_CLASSES = [
    "industrial_fire",
    "persistent_industrial_thermal_source",
    "agricultural_vegetation_fire",
    "natural_thermal_event",
    "possible_false_positive",
]


def load_tool(name):
    """Load a backend/*.py tool script as a module for testing."""

    import importlib.util

    path = (
        Path(__file__)
        .resolve()
        .parents[1]
        / name
    )

    spec = importlib.util.spec_from_file_location(
        name.replace(".py", ""),
        path,
    )

    module = importlib.util.module_from_spec(
        spec
    )

    spec.loader.exec_module(module)

    return module


def seed_real_event(
    factory,
    event_id="TG-test-real-1",
):
    """Insert one real (non-demo) event for exporter tests."""

    payload = {
        "id": event_id,
        "is_demo": False,
        "latitude": 21.1,
        "longitude": 72.6,
        "start_time":
            "2026-09-10T08:24:00+00:00",
        "last_seen_time":
            "2026-09-10T08:24:00+00:00",
        "features": {
            "mean_frp": 9.9,
            "max_frp": 16.7,
        },
        "context": {
            "osm_context_available": True,
            "satellite_context_available":
                False,
            "landuse_class": "industrial",
            "facilities": [
                {"name": "Plant A"},
                {"name": None},
            ],
        },
        "history": {},
        "risk": {
            "risk_score": 33,
            "risk_level": "Medium",
            "abnormality": {
                "abnormality_score": 70.6,
                "abnormality_status":
                    "above_baseline",
            },
        },
    }

    with factory() as db:
        db.add(
            Event(
                id=event_id,
                is_demo=False,
                payload=payload,
            )
        )

        db.commit()

    return event_id


def valid_reviewed_rows(
    count,
    groups=10,
    classes=REVIEW_CLASSES,
):
    """Generate complete reviewed rows ready for training."""

    rows = []

    for index in range(count):
        rows.append(
            candidate_feature_row(
                f"e{index}",
                split_group=(
                    f"g{index % groups}"
                ),
                label=classes[
                    index % len(classes)
                ],
                reviewed="true",
                reviewer="Dr. Rao",
                source_reference=(
                    f"ref.example/{index}"
                ),
                mean_frp="5",
            )
        )

    return rows


def test_exporter_preserves_manual_fields(
    tmp_path,
    monkeypatch,
    client,
):
    _, factory = client

    event_id = seed_real_event(factory)

    exporter = load_tool(
        "export_review_candidates.py"
    )

    output = tmp_path / "out.csv"

    write_candidates(
        tmp_path,
        [
            candidate_feature_row(
                event_id,
                split_group="cohort-a",
                label="industrial_fire",
                reviewed="true",
                reviewer="Dr. Rao",
                source_reference=(
                    "news.example/fire-1"
                ),
            ),
        ],
    ).rename(
        tmp_path / "out.csv"
    )

    monkeypatch.setattr(
        exporter,
        "OUTPUT",
        output,
    )

    monkeypatch.setattr(
        exporter,
        "Session",
        factory,
    )

    exporter.main()

    with output.open(
        newline=""
    ) as file:
        saved = list(
            csv.DictReader(file)
        )

    assert len(saved) == 1

    row = saved[0]

    assert row["event_id"] == event_id
    assert row["split_group"] == "cohort-a"
    assert row["label"] == "industrial_fire"
    assert row["reviewed"] == "true"
    assert row["reviewer"] == "Dr. Rao"
    assert (
        row["source_reference"]
        == "news.example/fire-1"
    )

    # Feature columns follow ml.py ordering; assistance
    # columns carry reviewer context.
    assert (
        list(row.keys())
        == ml.TRAINING_COLUMNS
        + ml.ASSISTANCE_COLUMNS
    )

    assert row["mean_frp"] == "9.9"
    assert row["risk_score"] == "33"
    assert (
        row["nearby_facility_names"]
        == "Plant A"
    )

    # Determinism: a second export is byte-identical.
    first = output.read_text()

    exporter.main()

    assert output.read_text() == first


def test_exporter_excludes_demo_and_reports_removals(
    tmp_path,
    monkeypatch,
    client,
    capsys,
):
    _, factory = client

    event_id = seed_real_event(factory)

    with factory() as db:
        demo = db.scalars(
            select(Event).where(
                Event.is_demo == True  # noqa: E712
            )
        ).first()

        demo_id = demo.id

    exporter = load_tool(
        "export_review_candidates.py"
    )

    output = tmp_path / "out.csv"

    write_candidates(
        tmp_path,
        [
            candidate_feature_row(demo_id),
            candidate_feature_row("TG-stale-1"),
        ],
    ).rename(
        tmp_path / "out.csv"
    )

    monkeypatch.setattr(
        exporter,
        "OUTPUT",
        output,
    )

    monkeypatch.setattr(
        exporter,
        "Session",
        factory,
    )

    exporter.main()

    with output.open(
        newline=""
    ) as file:
        ids = {
            row["event_id"]
            for row in csv.DictReader(file)
        }

    assert ids == {event_id}

    # Demo events are never candidates; removed events
    # are reported, not silently destroyed.
    printed = capsys.readouterr().out

    assert "TG-stale-1" in printed
    assert demo_id not in ids


def test_exporter_does_not_duplicate_events(
    tmp_path,
    monkeypatch,
    client,
):
    _, factory = client

    seed_real_event(
        factory,
        "TG-test-real-2",
    )

    exporter = load_tool(
        "export_review_candidates.py"
    )

    output = tmp_path / "out.csv"

    monkeypatch.setattr(
        exporter,
        "OUTPUT",
        output,
    )

    monkeypatch.setattr(
        exporter,
        "Session",
        factory,
    )

    exporter.main()
    exporter.main()

    lines = (
        output.read_text()
        .strip()
        .splitlines()
    )

    assert len(lines) == 2  # header + 1 event


def test_candidate_validator_detects_duplicates_and_invalid():
    from app.intelligence import CLASSES

    rows = [
        candidate_feature_row(
            "e1",
            split_group="g1",
            label="industrial_fire",
            reviewed="true",
            reviewer="r",
            source_reference="https://example.org/evidence/record-1",
            mean_frp="5",
        ),
        # Same event in a different split group.
        candidate_feature_row(
            "e1",
            split_group="g2",
            label="industrial_fire",
            reviewed="true",
            reviewer="r",
            source_reference="https://example.org/evidence/record-1",
            mean_frp="5",
        ),
        candidate_feature_row(
            "e2",
            label="not_a_class",
        ),
        candidate_feature_row(
            "e3",
            reviewed="maybe",
        ),
    ]

    import tempfile

    with tempfile.TemporaryDirectory() as folder:
        path = write_candidates(
            Path(folder),
            rows,
        )

        report = ml.candidate_report(path)

    problems = "\n".join(
        report["problems"]
    )

    assert (
        "Duplicate event_id: e1"
        in problems
    )

    assert (
        "Event appears in multiple split groups: e1"
        in problems
    )

    assert "e2: not_a_class" in problems

    assert (
        "1 row(s) with invalid reviewed value"
        in problems
    )

    assert not report["training_ready"]


def test_candidate_validator_demo_reviewed_rejected():
    import tempfile

    rows = [
        candidate_feature_row(
            "e1",
            split_group="g1",
            label="industrial_fire",
            reviewed="true",
            reviewer="r",
            source_reference="https://example.org/evidence/record-1",
            is_demo="true",
            mean_frp="5",
        ),
    ]

    with tempfile.TemporaryDirectory() as folder:
        report = ml.candidate_report(
            write_candidates(
                Path(folder),
                rows,
            )
        )

    problems = "\n".join(
        report["problems"]
    )

    assert (
        "is_demo=true" in problems
    )

    assert report["eligible_rows"] == 0


def test_candidate_validator_missing_source_reference():
    import tempfile

    rows = [
        candidate_feature_row(
            "e1",
            split_group="g1",
            label="industrial_fire",
            reviewed="true",
            reviewer="r",
            mean_frp="5",
        ),
    ]

    with tempfile.TemporaryDirectory() as folder:
        report = ml.candidate_report(
            write_candidates(
                Path(folder),
                rows,
            )
        )

    problems = "\n".join(
        report["problems"]
    )

    assert (
        "e1: missing source_reference"
        in problems
    )

    assert report["eligible_rows"] == 0


def test_candidate_unreviewed_and_incomplete_not_eligible():
    import tempfile

    rows = [
        # reviewed=false: never eligible, even when complete.
        candidate_feature_row(
            "e1",
            split_group="g1",
            label="industrial_fire",
            reviewed="false",
            reviewer="r",
            source_reference="https://example.org/evidence/record-1",
            mean_frp="5",
        ),
        # reviewed=true but split_group missing.
        candidate_feature_row(
            "e2",
            label="industrial_fire",
            reviewed="true",
            reviewer="r",
            source_reference="https://example.org/evidence/record-1",
            mean_frp="5",
        ),
        # reviewed=true but reviewer missing.
        candidate_feature_row(
            "e3",
            split_group="g1",
            label="industrial_fire",
            reviewed="true",
            source_reference="https://example.org/evidence/record-1",
            mean_frp="5",
        ),
    ]

    with tempfile.TemporaryDirectory() as folder:
        report = ml.candidate_report(
            write_candidates(
                Path(folder),
                rows,
            )
        )

    assert report["reviewed_rows"] == 2

    assert report["eligible_rows"] == 0

    problems = "\n".join(
        report["problems"]
    )

    assert "e2: missing split_group" in problems

    assert "e3: missing reviewer" in problems


def test_candidate_validator_missing_feature_columns():
    import tempfile

    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "c.csv"

        path.write_text(
            "event_id,split_group,label,"
            "reviewed,reviewer,"
            "source_reference,is_demo\n"
        )

        report = ml.candidate_report(
            path
        )

    assert (
        len(
            report[
                "feature_columns_missing"
            ]
        )
        == len(FEATURES)
    )

    problems = "\n".join(
        report["problems"]
    )

    assert (
        "Missing feature columns required by ml.py"
        in problems
    )


def test_candidate_validator_extra_columns_ignored():
    import tempfile

    from app.ml import ASSISTANCE_COLUMNS

    rows = valid_reviewed_rows(
        30,
        classes=REVIEW_CLASSES,
    )

    with tempfile.TemporaryDirectory() as folder:
        report = ml.candidate_report(
            write_candidates(
                Path(folder),
                rows,
            )
        )

    # Assistance columns are recognized as ignorable
    # context, never as problems or features.
    assert (
        report["extra_columns_ignored"]
        == ASSISTANCE_COLUMNS
    )

    assert report["eligible_rows"] == 30

    assert not (
        set(ASSISTANCE_COLUMNS)
        & set(FEATURES)
    )


def test_candidate_validator_gate_below_30_rows():
    import tempfile

    rows = valid_reviewed_rows(
        29,
        classes=REVIEW_CLASSES,
    )

    with tempfile.TemporaryDirectory() as folder:
        report = ml.candidate_report(
            write_candidates(
                Path(folder),
                rows,
            )
        )

    assert not report["training_ready"]

    assert (
        "1 more reviewed events"
        in report["missing"]
    )


def test_candidate_validator_gate_missing_class():
    import tempfile

    rows = valid_reviewed_rows(
        30,
        classes=REVIEW_CLASSES[:4],
    )

    with tempfile.TemporaryDirectory() as folder:
        report = ml.candidate_report(
            write_candidates(
                Path(folder),
                rows,
            )
        )

    assert not report["training_ready"]

    assert (
        REVIEW_CLASSES[4]
        in report["missing"]
    )


def test_candidate_validator_gate_below_10_groups():
    import tempfile

    rows = valid_reviewed_rows(
        30,
        groups=9,
        classes=REVIEW_CLASSES,
    )

    with tempfile.TemporaryDirectory() as folder:
        report = ml.candidate_report(
            write_candidates(
                Path(folder),
                rows,
            )
        )

    assert not report["training_ready"]

    assert (
        "1 more independent split groups"
        in report["missing"]
    )


def test_candidate_validator_valid_dataset_ready():
    import tempfile

    rows = valid_reviewed_rows(
        30,
        classes=REVIEW_CLASSES,
    )

    with tempfile.TemporaryDirectory() as folder:
        report = ml.candidate_report(
            write_candidates(
                Path(folder),
                rows,
            )
        )

    assert report["training_ready"]
    assert report["problems"] == []
    assert report["classes_present"] == 5
    assert report["split_groups"] == 10
    assert report["eligible_rows"] == 30


def test_finalizer_writes_training_schema():
    import tempfile

    finalizer = load_tool(
        "finalize_reviewed_labels.py"
    )

    rows = valid_reviewed_rows(
        30,
        classes=REVIEW_CLASSES,
    )

    # Unreviewed rows must be filtered out.
    rows += [
        candidate_feature_row(
            "unreviewed-1",
            label="industrial_fire",
        ),
    ]

    with tempfile.TemporaryDirectory() as folder:
        candidates = write_candidates(
            Path(folder),
            rows,
        )

        output = (
            Path(folder)
            / "reviewed_labels.csv"
        )

        monkeypatch_free = {
            "CANDIDATES": candidates,
            "OUTPUT": output,
        }

        original = {
            key: getattr(
                finalizer,
                key,
            )
            for key in monkeypatch_free
        }

        for key, value in monkeypatch_free.items():
            setattr(
                finalizer,
                key,
                value,
            )

        try:
            finalizer.main()
        finally:
            for key, value in original.items():
                setattr(
                    finalizer,
                    key,
                    value,
                )

        with output.open(
            newline=""
        ) as file:
            reader = csv.DictReader(file)

            saved = list(reader)

            header = reader.fieldnames

        assert (
            header == ml.TRAINING_COLUMNS
        )

        # Assistance columns must not leak into
        # the published training file.
        assert (
            "risk_score" not in header
        )

        assert (
            "latitude" not in header
        )

        assert len(saved) == 30

        assert all(
            row["reviewed"] == "true"
            for row in saved
        )

        assert all(
            row["event_id"]
            != "unreviewed-1"
            for row in saved
        )


def test_finalizer_refuses_incomplete_reviewed_row():
    import tempfile

    finalizer = load_tool(
        "finalize_reviewed_labels.py"
    )

    rows = [
        candidate_feature_row(
            "e1",
            split_group="g1",
            label="industrial_fire",
            reviewed="true",
            reviewer="r",
            # source_reference missing -> refusal
            mean_frp="5",
        ),
    ]

    with tempfile.TemporaryDirectory() as folder:
        candidates = write_candidates(
            Path(folder),
            rows,
        )

        output = (
            Path(folder)
            / "reviewed_labels.csv"
        )

        original = (
            finalizer.CANDIDATES,
            finalizer.OUTPUT,
        )

        finalizer.CANDIDATES = candidates
        finalizer.OUTPUT = output

        try:
            with pytest.raises(
                SystemExit
            ) as exit_info:
                finalizer.main()

            assert (
                exit_info.value.code == 1
            )
        finally:
            finalizer.CANDIDATES, (
                finalizer.OUTPUT
            ) = original

        assert not output.exists()


def test_finalizer_refuses_invalid_label_and_demo():
    import tempfile

    finalizer = load_tool(
        "finalize_reviewed_labels.py"
    )

    rows = [
        candidate_feature_row(
            "e1",
            split_group="g1",
            label="not_a_class",
            reviewed="true",
            reviewer="r",
            source_reference="https://example.org/evidence/record-1",
            mean_frp="5",
        ),
        candidate_feature_row(
            "e2",
            split_group="g1",
            label="industrial_fire",
            reviewed="true",
            reviewer="r",
            source_reference="https://example.org/evidence/record-1",
            is_demo="true",
            mean_frp="5",
        ),
    ]

    with tempfile.TemporaryDirectory() as folder:
        candidates = write_candidates(
            Path(folder),
            rows,
        )

        output = (
            Path(folder)
            / "reviewed_labels.csv"
        )

        original = (
            finalizer.CANDIDATES,
            finalizer.OUTPUT,
        )

        finalizer.CANDIDATES = candidates
        finalizer.OUTPUT = output

        try:
            with pytest.raises(
                SystemExit
            ):
                finalizer.main()
        finally:
            finalizer.CANDIDATES, (
                finalizer.OUTPUT
            ) = original

        assert not output.exists()


def test_assistance_columns_never_become_training_features():
    import tempfile

    from app.ml import ASSISTANCE_COLUMNS

    assert (
        ml.TRAINING_COLUMNS
        == ml.REVIEW_META + list(FEATURES)
    )

    assert not (
        set(ASSISTANCE_COLUMNS)
        & set(FEATURES)
    )

    rows = [
        candidate_feature_row(
            "e1",
            split_group="g1",
            label="industrial_fire",
            reviewed="true",
            reviewer="r",
            source_reference="https://example.org/evidence/record-1",
            mean_frp="5",
            # Decoy values in assistance columns.
            risk_score="99999",
            latitude="999",
        ),
    ]

    with tempfile.TemporaryDirectory() as folder:
        path = write_candidates(
            Path(folder),
            rows,
        )

        eligible = ml.dataset(path)

    assert len(eligible) == 1

    vector = features(eligible[0])

    assert len(vector) == len(FEATURES)

    assert vector[
        FEATURES.index("mean_frp")
    ] == 5.0

    # Neither decoy value appears anywhere in the
    # training vector.
    assert 99999.0 not in vector
    assert 999.0 not in vector


def test_review_endpoints_readonly_and_scoped(
    client,
    tmp_path,
    monkeypatch,
):
    import tempfile

    c, _ = client

    admin_headers = auth(c)

    operator_headers = auth(c, True)

    # Review readiness is open to authenticated users.
    monkeypatch.setattr(
        ml,
        "CANDIDATES",
        tmp_path / "missing.csv",
    )

    response = c.get(
        "/api/v1/model/review-readiness",
        headers=operator_headers,
    )

    assert response.status_code == 200

    body = response.json()

    assert body[
        "candidates_file"
    ] is False

    assert (
        body["training_ready"] is False
    )

    # Candidate export is admin-only.
    assert (
        c.get(
            "/api/v1/model/review-candidates",
            headers=operator_headers,
        ).status_code
        == 403
    )

    assert (
        c.get(
            "/api/v1/model/review-candidates",
            headers=admin_headers,
        ).status_code
        == 404
    )

    with tempfile.TemporaryDirectory() as folder:
        candidates = write_candidates(
            Path(folder),
            [
                candidate_feature_row(
                    "TG-e1"
                ),
            ],
        )

        monkeypatch.setattr(
            ml,
            "CANDIDATES",
            candidates,
        )

        response = c.get(
            "/api/v1/model/review-candidates",
            headers=admin_headers,
        )

    assert response.status_code == 200

    body = response.json()

    assert body["count"] == 1

    assert (
        body["candidates"][0]["event_id"]
        == "TG-e1"
    )


def candidate_csv(
    rows,
    include_assistance=True,
):
    """Build candidate CSV text with the exact exporter schema."""

    from app.ml import (
        REVIEW_META,
        ASSISTANCE_COLUMNS,
    )

    import io

    columns = (
        REVIEW_META
        + list(FEATURES)
        + (
            ASSISTANCE_COLUMNS
            if include_assistance
            else []
        )
    )

    buffer = io.StringIO()

    writer = csv.DictWriter(
        buffer,
        fieldnames=columns,
        extrasaction="ignore",
    )

    writer.writeheader()

    base = {
        column: ""
        for column in columns
    }

    for row in rows:
        item = {
            **base,
            **row,
        }

        writer.writerow(item)

    return buffer.getvalue()


def write_candidates(
    tmp_path,
    rows,
    include_assistance=True,
):
    path = tmp_path / "candidates.csv"

    path.write_text(
        candidate_csv(
            rows,
            include_assistance,
        )
    )

    return path


def candidate_feature_row(
    event_id,
    **overrides,
):
    """Minimal event row; every feature empty means imputation."""

    return {
        "event_id": event_id,
        "split_group": "",
        "label": "",
        "reviewed": "false",
        "reviewer": "",
        "source_reference": "",
        "is_demo": "false",
        **overrides,
    }
