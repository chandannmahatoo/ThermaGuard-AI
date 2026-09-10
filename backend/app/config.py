from pathlib import Path
import secrets

from pydantic import model_validator
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


class Settings(BaseSettings):
    # Always load backend/.env regardless of current working directory
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
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

    # -----------------------------------------------------
    # Event clustering
    # -----------------------------------------------------

    event_cluster_radius_km: float = 2.0
    event_cluster_time_hours: float = 24.0

    # -----------------------------------------------------
    # Risk / Alerts
    # -----------------------------------------------------

    auto_alert_risk_threshold: int = 80

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

    cors_origins: str = "http://localhost:3000"

    # -----------------------------------------------------
    # Ollama AI Copilot
    # -----------------------------------------------------

    ollama_enabled: bool = False
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = ""

    # -----------------------------------------------------
    # SMTP
    # -----------------------------------------------------

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

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

        if self.smtp_port <= 0 or self.smtp_port > 65535:
            raise ValueError(
                "SMTP_PORT must be between 1 and 65535"
            )

    # -----------------------------------------------------
    # Convenience helpers
    # -----------------------------------------------------

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
    def ollama_configured(self) -> bool:
        return bool(
            self.ollama_enabled
            and self.ollama_base_url
            and self.ollama_model
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