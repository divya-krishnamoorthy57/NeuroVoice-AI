import os
import urllib.parse
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "neurovoice_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "NeuroVoice@123")
DB_NAME = os.getenv("DB_NAME", "neurovoice")

encoded_password = urllib.parse.quote_plus(DB_PASSWORD)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"mysql+pymysql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
)

SECRET_KEY = os.getenv("SECRET_KEY", "neurovoice_super_secret_jwt_key_2026_production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

FRONTEND_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://127.0.0.1:5173,http://127.0.0.1:5174,http://127.0.0.1:5175"
    ).split(",")
    if origin.strip()
]
