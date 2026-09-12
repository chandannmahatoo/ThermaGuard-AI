from pathlib import Path
import secrets
import logging

from pydantic import model_validator, Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict


# ---------------------------------------------------------
# Environment file path
# ---------------------------------------------------------

BACKEND_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BACKEND_DIR / ".env"


# ---------------------------------------------------------
# Risk configuration
# ---------------------------------------------------------

REQUIRED_RISK_WEIGHT_KEYS = (
    "thermal_severity",
    "persistence",
    "industrial_proximity",
    "residential_proximity",
    "infrastructure_exposure",
    "classification_context",
    "historical_abnormality",
)


# Supported hotspot schemas; availability/date ranges are always discovered remotely.
FIRMS_SOURCES = {
    'VIIRS_SNPP_NRT': ('nrt', 'VIIRS'),
    'VIIRS_NOAA20_NRT': ('nrt', 'VIIRS'),
    'VIIRS_NOAA21_NRT': ('nrt', 'VIIRS'),
    'MODIS_NRT': ('nrt', 'MODIS'),
    'VIIRS_SNPP_SP': ('sp', 'VIIRS'),
    'VIIRS_NOAA20_SP': ('sp', 'VIIRS'),
    'MODIS_SP': ('sp', 'MODIS'),
}


class Settings(BaseSettings):
    # Always load backend/.env regardless of current working directory
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        hide_input_in_errors=True,
    )

    # -----------------------------------------------------
    # Database
    # -----------------------------------------------------

    database_url: str = "sqlite:///./thermaguard.db"

    # -----------------------------------------------------
    # Authentication
    # -----------------------------------------------------

    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 720

    # -----------------------------------------------------
    # NASA FIRMS
    # -----------------------------------------------------

    firms_map_key: str = ""
    firms_live_sources: str = "VIIRS_SNPP_NRT"
    firms_availability_url: str = "https://firms.modaps.eosdis.nasa.gov/api/data_availability/csv"
    firms_max_requests: int = 12

    @property
    def live_sources(self):
        return [value.strip() for value in self.firms_live_sources.split(',') if value.strip()]

    @model_validator(mode='after')
    def validate_firms_sources(self):
        sources = self.live_sources
        if (not sources or len(sources) != len(set(sources))
                or any(source not in FIRMS_SOURCES or FIRMS_SOURCES[source][0] != 'nrt' for source in sources)):
            raise ValueError('FIRMS_LIVE_SOURCES must contain distinct supported NRT sources')
        if not 1 <= self.firms_max_requests <= 12 or len(sources) > self.firms_max_requests:
            raise ValueError('FIRMS request budget must be 1..12 and cover configured sources')
        if self.gemini_enabled and (not self.gemini_api_key.strip() or not self.gemini_model.strip()):
            raise ValueError('Enabled Gemini requires GEMINI_API_KEY and GEMINI_MODEL')
        if self.smtp_enabled and not self.smtp_configured:
            raise ValueError('Enabled SMTP requires SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD and SMTP_FROM')
        return self

    firms_api_url: str = (
        "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
    )

    # -----------------------------------------------------
    # OpenStreetMap / Overpass
    # -----------------------------------------------------

    overpass_api_url: str = (
        "https://overpass-api.de/api/interpreter"
    )

    # -----------------------------------------------------
    # Satellite context - Copernicus
    # -----------------------------------------------------

    satellite_provider: str = "copernicus"

    copernicus_client_id: str = ""
    copernicus_client_secret: str = ""

    copernicus_token_url: str = (
        "https://identity.dataspace.copernicus.eu/"
        "auth/realms/CDSE/protocol/openid-connect/token"
    )

    copernicus_base_url: str = (
        "https://sh.dataspace.copernicus.eu"
    )

    # -----------------------------------------------------
    # Runtime / Demo mode
    # -----------------------------------------------------

    demo_mode: bool = True

    # -----------------------------------------------------
    # Synchronization limits
    # -----------------------------------------------------

    max_sync_observations: int = 500
    osm_events_per_sync: int = 5
    satellite_events_per_sync: int = 5
    firms_timeout_seconds: float = 30
    osm_timeout_seconds: float = 20
    copernicus_token_timeout_seconds: float = 15
    copernicus_stats_timeout_seconds: float = 20

    # -----------------------------------------------------
    # Event clustering
    # -----------------------------------------------------

    event_cluster_radius_km: float = 2.0
    event_cluster_time_hours: float = 24.0

    # -----------------------------------------------------
    # Risk / Alerts
    # -----------------------------------------------------

    auto_alert_risk_threshold: int = Field(80, validation_alias=AliasChoices("ALERT_RISK_THRESHOLD", "AUTO_ALERT_RISK_THRESHOLD", "auto_alert_risk_threshold"))
    default_alert_radius_km: float = Field(10, gt=0, le=500)

    risk_weights: dict[str, float] = {
        "thermal_severity": 50.0,
        "persistence": 10.0,
        "industrial_proximity": 10.0,
        "residential_proximity": 10.0,
        "infrastructure_exposure": 5.0,
        "classification_context": 5.0,
        "historical_abnormality": 10.0,
    }

    # -----------------------------------------------------
    # CORS
    # -----------------------------------------------------

    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # -----------------------------------------------------
    # Gemini AI Copilot
    # -----------------------------------------------------

    gemini_enabled: bool = False
    gemini_api_key: str = Field("", repr=False)
    gemini_model: str = ""
    gemini_timeout_seconds: float = Field(30, gt=0, le=120)

    # -----------------------------------------------------
    # SMTP
    # -----------------------------------------------------

    smtp_enabled: bool = False
    smtp_timeout_seconds: float = Field(20, gt=0, le=120)
    smtp_test_recipient: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = Field("", repr=False)
    smtp_from: str = ""

    # Optional evidence providers; never Model V1 inputs.
    weather_enabled: bool = False
    weather_provider: str = "open_meteo"
    weather_api_url: str = "https://api.open-meteo.com/v1/forecast"
    weather_timeout_seconds: float = Field(15, gt=0, le=60)
    weather_events_per_sync: int = Field(10, ge=0, le=20)
    air_quality_enabled: bool = False
    air_quality_provider: str = "open_meteo"
    air_quality_api_url: str = "https://air-quality-api.open-meteo.com/v1/air-quality"
    air_quality_timeout_seconds: float = Field(15, gt=0, le=60)
    air_quality_events_per_sync: int = Field(10, ge=0, le=20)
    geocoding_enabled: bool = False
    geocoding_provider: str = "nominatim"
    geocoding_api_url: str = "https://nominatim.openstreetmap.org/reverse"
    geocoding_timeout_seconds: float = Field(10, gt=0, le=60)
    geocoding_events_per_sync: int = Field(10, ge=0, le=20)
    eonet_enabled: bool = False
    eonet_api_url: str = "https://eonet.gsfc.nasa.gov/api/v3/events"
    eonet_timeout_seconds: float = Field(15, gt=0, le=60)
    eonet_events_per_sync: int = Field(10, ge=0, le=20)
    geocoding_user_agent: str = "ThermaGuardAI/1.0"
    routing_enabled: bool = False
    openrouteservice_api_key: str = Field("", repr=False)
    openrouteservice_api_url: str = "https://api.openrouteservice.org"
    routing_timeout_seconds: float = Field(15, gt=0, le=60)
    push_notifications_enabled: bool = False
    firebase_project_id: str = ""
    firebase_credentials_path: str = Field("", repr=False)

    @model_validator(mode="after")
    def validate_context_providers(self):
        from urllib.parse import urlsplit
        for name, expected in (("weather", "open_meteo"), ("air_quality", "open_meteo"), ("geocoding", "nominatim")):
            if getattr(self, name+"_provider") != expected:
                raise ValueError(name.upper()+"_PROVIDER is unsupported")
        for name in ("weather", "air_quality", "geocoding", "eonet", "openrouteservice"):
            url = urlsplit(getattr(self, name+"_api_url"))
            if url.scheme != "https" or not url.netloc or url.username or url.password or url.query or url.fragment:
                raise ValueError(name.upper()+"_API_URL must be an HTTPS URL without credentials or query")
        if not self.geocoding_user_agent.strip():
            raise ValueError("GEOCODING_USER_AGENT is required")
        return self

    # -----------------------------------------------------
    # Validation
    # -----------------------------------------------------

    @model_validator(mode="after")
    def validate_settings(self):
        self._validate_risk_weights()
        self._validate_runtime_settings()
        return self

    def _validate_risk_weights(self) -> None:
        weights = self.risk_weights

        missing = [
            key
            for key in REQUIRED_RISK_WEIGHT_KEYS
            if key not in weights
        ]

        if missing:
            raise ValueError(
                "RISK_WEIGHTS missing keys: "
                + ", ".join(missing)
            )

        unknown = [
            key
            for key in weights
            if key not in REQUIRED_RISK_WEIGHT_KEYS
        ]

        if unknown:
            raise ValueError(
                "RISK_WEIGHTS contains unknown keys: "
                + ", ".join(unknown)
            )

        negative = [
            key
            for key, value in weights.items()
            if value < 0
        ]

        if negative:
            raise ValueError(
                "RISK_WEIGHTS must not contain negative values: "
                + ", ".join(negative)
            )

        total = round(sum(weights.values()), 6)

        if total != 100:
            raise ValueError(
                f"RISK_WEIGHTS must total exactly 100 "
                f"(current total: {total})"
            )

    def _validate_runtime_settings(self) -> None:
        import math
        for key in ('satellite_events_per_sync', 'firms_timeout_seconds', 'osm_timeout_seconds',
                    'copernicus_token_timeout_seconds', 'copernicus_stats_timeout_seconds'):
            value = getattr(self, key)
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f'{key.upper()} must be finite and greater than 0')
        if not 0 <= self.auto_alert_risk_threshold <= 100:
            raise ValueError(
                "AUTO_ALERT_RISK_THRESHOLD must be between 0 and 100"
            )

        if self.event_cluster_radius_km <= 0:
            raise ValueError(
                "EVENT_CLUSTER_RADIUS_KM must be greater than 0"
            )

        if self.event_cluster_time_hours <= 0:
            raise ValueError(
                "EVENT_CLUSTER_TIME_HOURS must be greater than 0"
            )

        if self.max_sync_observations <= 0:
            raise ValueError(
                "MAX_SYNC_OBSERVATIONS must be greater than 0"
            )

        if self.osm_events_per_sync <= 0:
            raise ValueError(
                "OSM_EVENTS_PER_SYNC must be greater than 0"
            )

        if self.gemini_timeout_seconds <= 0:
            raise ValueError(
                "GEMINI_TIMEOUT_SECONDS must be greater than 0"
            )

        if self.smtp_port <= 0 or self.smtp_port > 65535:
            raise ValueError(
                "SMTP_PORT must be between 1 and 65535"
            )

    # -----------------------------------------------------
    # Convenience helpers
    # -----------------------------------------------------

    @property
    def allowed_cors_origins(self):
        origins = [o.strip() for o in self.cors_origins.split(',') if o.strip()]
        local = ['http://localhost:3000', 'http://127.0.0.1:3000']
        if any(o in origins for o in local):
            origins = list(dict.fromkeys(origins + local))
        return origins

    @property
    def satellite_credentials_present(self) -> bool:
        return bool(
            self.copernicus_client_id
            and self.copernicus_client_secret
            and self.copernicus_token_url
            and self.copernicus_base_url
        )

    @property
    def firms_credentials_present(self) -> bool:
        return bool(self.firms_map_key)

    @property
    def smtp_configured(self) -> bool:
        return bool(
            self.smtp_host
            and self.smtp_user
            and self.smtp_password
            and self.smtp_from
        )

    @property
    def gemini_configured(self) -> bool:
        return bool(
            self.gemini_enabled
            and self.gemini_api_key.strip()
            and self.gemini_model.strip()
        )


# ---------------------------------------------------------
# Initialize settings
# ---------------------------------------------------------

settings = Settings()


# ---------------------------------------------------------
# JWT safety
# ---------------------------------------------------------

if not settings.jwt_secret:
    if not settings.demo_mode:
        raise RuntimeError(
            "JWT_SECRET is required outside demo mode"
        )

    # Safe temporary secret for local demo mode only
    settings.jwt_secret = secrets.token_urlsafe(48)