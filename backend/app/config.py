from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:postgrespassword@localhost:5432/threat_intel"
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "threatpassword"
    SECRET_KEY: str = "threat_intel_dev_secret_key_change_in_prod_12345"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    AUTOSCAN_ENABLED: bool = False
    AUTOSCAN_DEFAULT_INTERVAL_MINUTES: int = 180
    AUTOSCAN_ALLOWED_HOSTS: str = "127.0.0.1,localhost"
    class Config:
        env_file = ".env"
settings = Settings()
