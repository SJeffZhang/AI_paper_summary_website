from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Paper Summary API"
    DATABASE_URL: str = "mysql+pymysql://root:password@localhost:3306/ai_paper_summary"
    KIMI_API_KEY: str = ""
    HUGGINGFACE_API_URL: str = "https://huggingface.co/api/daily_papers"
    FRONTEND_URL: str = "http://localhost:5173"
    
    class Config:
        env_file = ".env"

settings = Settings()