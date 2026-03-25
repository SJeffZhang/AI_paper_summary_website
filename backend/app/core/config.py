from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Paper Summary API"
    DATABASE_URL: str = "mysql+pymysql://root:password@localhost:3306/ai_paper_summary"
    KIMI_API_KEY: str = ""
    KIMI_BASE_URL: str = "https://api.moonshot.cn/v1"
    KIMI_MODEL: str = "kimi-k2.5"
    KIMI_TIMEOUT_SECONDS: int = 60
    KIMI_LONGFORM_TIMEOUT_SECONDS: int = 180
    KIMI_MAX_RETRIES: int = 3
    KIMI_TITLE_BATCH_SIZE: int = 8
    PIPELINE_PROBE_DAYS: int = 14
    MYSQL_UNIX_SOCKET: str = ""
    HUGGINGFACE_API_URL: str = "https://huggingface.co/api/daily_papers"
    FRONTEND_URL: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
