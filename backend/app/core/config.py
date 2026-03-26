from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Paper Summary API"
    DATABASE_URL: str = "mysql+pymysql://root:password@localhost:3306/ai_paper_summary"
    BACKEND_PUBLIC_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:5173"
    KIMI_API_KEY: str = ""
    KIMI_BASE_URL: str = "https://api.moonshot.cn/v1"
    KIMI_MODEL: str = "kimi-k2.5"
    KIMI_TIMEOUT_SECONDS: int = 60
    KIMI_LONGFORM_TIMEOUT_SECONDS: int = 180
    KIMI_MAX_RETRIES: int = 3
    KIMI_TITLE_BATCH_SIZE: int = 8
    PIPELINE_PROBE_DAYS: int = 14
    MYSQL_UNIX_SOCKET: str = ""
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "AI Paper Summary"
    SMTP_USE_STARTTLS: bool = True
    SMTP_USE_SSL: bool = False
    OWNER_ALERT_EMAIL: str = "z1332556430@gmail.com"
    HUGGINGFACE_API_URL: str = "https://huggingface.co/api/daily_papers"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
