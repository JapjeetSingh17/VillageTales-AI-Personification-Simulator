import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    gemini_tts_model: str = os.getenv("GEMINI_TTS_MODEL", "gemini-3.1-flash-tts-preview")
    gemini_stt_model: str = os.getenv("GEMINI_STT_MODEL", "gemini-3.5-transcribe")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
