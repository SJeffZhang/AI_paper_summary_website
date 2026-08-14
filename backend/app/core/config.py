from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Paper Summary API"
    DATABASE_URL: str = "mysql+pymysql://root:password@localhost:3306/ai_paper_summary"
    BACKEND_PUBLIC_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:5173"
    DEEPSEEK_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.deepseek.com"
    LLM_MODEL: str = "deepseek-v4-flash"
    LLM_THINKING_ENABLED: bool = False
    LLM_TIMEOUT_SECONDS: int = 60
    LLM_LONGFORM_TIMEOUT_SECONDS: int = 180
    LLM_MAX_RETRIES: int = 3
    LLM_LONGFORM_MAX_RETRIES: int = 2
    LLM_MIN_REQUEST_INTERVAL_SECONDS: float = 1.0
    LLM_LONGFORM_MIN_REQUEST_INTERVAL_SECONDS: float = 2.0
    LLM_EDITOR_MAX_TOKENS: int = 4096
    LLM_WRITER_FOCUS_MAX_TOKENS: int = 4096
    LLM_WRITER_WATCHING_MAX_TOKENS: int = 4096
    LLM_REVIEWER_MAX_TOKENS: int = 2048
    LLM_ABSTRACT_MAX_CHARS: int = 16000
    LLM_TITLE_LOCALIZATION_ATTEMPTS: int = 3
    LLM_TITLE_BATCH_SIZE: int = 8
    LLM_USAGE_LOG_PATH: str = ""
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
    AFFILIATION_ENRICH_ENABLED: bool = True
    AFFILIATION_ENRICH_TIMEOUT_SECONDS: int = 30
    AFFILIATION_ENRICH_MAX_RETRIES: int = 5
    AFFILIATION_ENRICH_PAGE_TEXT_MIN_CHARS: int = 200

    @property
    def LLM_API_KEY(self) -> str:
        return self.DEEPSEEK_API_KEY.strip()

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
