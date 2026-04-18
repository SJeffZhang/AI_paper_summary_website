from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Paper Summary API"
    DATABASE_URL: str = "mysql+pymysql://root:password@localhost:3306/ai_paper_summary"
    BACKEND_PUBLIC_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:5173"
    KIMI_API_KEY: str = ""
    MINIMAX_API_KEY: str = ""
    KIMI_BASE_URL: str = "https://api.minimaxi.com/v1"
    KIMI_MODEL: str = "MiniMax-M2.5"
    KIMI_TIMEOUT_SECONDS: int = 60
    KIMI_LONGFORM_TIMEOUT_SECONDS: int = 180
    KIMI_MAX_RETRIES: int = 3
    KIMI_LONGFORM_MAX_RETRIES: int = 2
    KIMI_MIN_REQUEST_INTERVAL_SECONDS: float = 5.0
    KIMI_LONGFORM_MIN_REQUEST_INTERVAL_SECONDS: float = 20.0
    KIMI_EDITOR_MAX_TOKENS: int = 4096
    KIMI_WRITER_FOCUS_MAX_TOKENS: int = 4096
    KIMI_WRITER_WATCHING_MAX_TOKENS: int = 4096
    KIMI_REVIEWER_MAX_TOKENS: int = 2048
    KIMI_TITLE_LOCALIZATION_ATTEMPTS: int = 3
    KIMI_TITLE_BATCH_SIZE: int = 8
    PIPELINE_MAX_CATEGORY_ATTEMPTS: int = 30
    PIPELINE_FOCUS_ATTEMPT_MULTIPLIER: int = 4
    PIPELINE_WATCHING_ATTEMPT_MULTIPLIER: int = 2
    PIPELINE_REVIEW_REQUEUE_ATTEMPTS: int = 5
    PIPELINE_ENABLE_WATCHING: bool = True
    PIPELINE_REVIEWER_STRICT: bool = True
    PIPELINE_PROBE_DAYS: int = 14
    PIPELINE_FETCH_BACKTRACK_DAYS: int = 3
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
    SEMANTIC_SCHOLAR_TIMEOUT_SECONDS: int = 5
    CRAWLER_CITATION_MAX_WORKERS: int = 16

    @property
    def LLM_API_KEY(self) -> str:
        return (self.MINIMAX_API_KEY or self.KIMI_API_KEY or "").strip()

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
