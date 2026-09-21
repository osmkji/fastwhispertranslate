from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    API_KEY: str = "ma_cle_secrete_laravel_123"
    MODEL_SIZE: str = "small"
    DEVICE: str = "cpu"
    COMPUTE_TYPE: str = "int8"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    class Config:
        env_file = ".env"

settings = Settings()
