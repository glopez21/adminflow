"""AdminFlow Configuration Settings using Pydantic Settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    ad_server: str = Field(default="dc01.yourdomain.com")
    ad_base_dn: str = Field(default="dc=yourdomain,dc=com")
    ad_user: str = Field(default="admin@yourdomain.com")
    ad_password: str = Field(default="")

    ldap_port: int = Field(default=389)
    ldaps_port: int = Field(default=636)

    default_ou: str = Field(default="ou=Users,dc=yourdomain,dc=com")
    default_group: str = Field(default="Domain Users")

    password_min_length: int = Field(default=12)
    password_require_uppercase: bool = Field(default=True)
    password_require_lowercase: bool = Field(default=True)
    password_require_numbers: bool = Field(default=True)
    password_require_special: bool = Field(default=True)
    password_max_age_days: int = Field(default=90)
    password_min_age_days: int = Field(default=1)
    lockout_threshold: int = Field(default=5)
    lockout_duration_minutes: int = Field(default=30)

    inactive_threshold_days: int = Field(default=90)

    report_output_dir: str = Field(default="reports")

    log_level: str = Field(default="INFO")
    log_file: str = Field(default="logs/ad_automation.log")

    database_url: str = Field(default="sqlite:///adminflow.db")

    redis_url: str = Field(default="redis://localhost:6379/0")

    api_secret_key: str = Field(default="change-me-in-production")
    jwt_secret_key: str = Field(default="change-me-in-production")
    jwt_algorithm: str = Field(default="HS256")
    jwt_expiration_minutes: int = Field(default=60)

    azure_tenant_id: str | None = Field(default=None)
    azure_client_id: str | None = Field(default=None)
    azure_client_secret: str | None = Field(default=None)

    cors_allowed_origins: list[str] = Field(default=["*"])
    cors_allow_credentials: bool = Field(default=True)

    api_key_ad_admin: str = Field(default="ad-admin-key-001")
    api_key_ad_auto: str = Field(default="ad-auto-key-002")
    api_key_ad_read: str = Field(default="ad-read-key-003")

    @property
    def password_policy(self) -> dict:
        """Get password policy as dictionary."""
        return {
            "min_length": self.password_min_length,
            "require_uppercase": self.password_require_uppercase,
            "require_lowercase": self.password_require_lowercase,
            "require_numbers": self.password_require_numbers,
            "require_special": self.password_require_special,
            "max_age_days": self.password_max_age_days,
            "min_age_days": self.password_min_age_days,
            "lockout_threshold": self.lockout_threshold,
            "lockout_duration_minutes": self.lockout_duration_minutes,
        }


settings = Settings()

AD_SERVER = settings.ad_server
AD_BASE_DN = settings.ad_base_dn
AD_USER = settings.ad_user
AD_PASSWORD = settings.ad_password

LDAP_PORT = settings.ldap_port
LDAPS_PORT = settings.ldaps_port

DEFAULT_OU = settings.default_ou
DEFAULT_GROUP = settings.default_group

PASSWORD_POLICY = settings.password_policy

INACTIVE_THRESHOLD_DAYS = settings.inactive_threshold_days

REPORT_OUTPUT_DIR = settings.report_output_dir

LOG_LEVEL = settings.log_level
LOG_FILE = settings.log_file

DATABASE_URL = settings.database_url
REDIS_URL = settings.redis_url

API_SECRET_KEY = settings.api_secret_key
JWT_SECRET_KEY = settings.jwt_secret_key
JWT_ALGORITHM = settings.jwt_algorithm
JWT_EXPIRATION_MINUTES = settings.jwt_expiration_minutes

AZURE_TENANT_ID = settings.azure_tenant_id
AZURE_CLIENT_ID = settings.azure_client_id
AZURE_CLIENT_SECRET = settings.azure_client_secret

CORS_ALLOWED_ORIGINS = settings.cors_allowed_origins
CORS_ALLOW_CREDENTIALS = settings.cors_allow_credentials
