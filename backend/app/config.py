from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:postgrespassword@localhost:5432/threat_intel"
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "threatpassword"
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    AUTOSCAN_ENABLED: bool = False
    AUTOSCAN_DEFAULT_INTERVAL_MINUTES: int = 180
    AUTOSCAN_ALLOWED_HOSTS: str = "127.0.0.1,localhost"
    CORS_ALLOWED_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.6-flash"
    SCANNER_TLS_VERIFY: bool = True
    SCANNER_CONNECT_TIMEOUT_SECONDS: int = 10
    SCANNER_MAX_RESPONSE_BYTES: int = 1_000_000
    # Synthetic filler evidence is excluded from correlation by default. Set true only for a controlled demo.
    CORRELATION_EXCLUDE_SYNTHETIC_DEMO_EVIDENCE: bool = True
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
settings = Settings()
