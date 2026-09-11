# VPP Simulator Application Package
from pathlib import Path

from dotenv import load_dotenv

# Local settings (DB credentials, JWT secret) from backend/.env, see .env.example
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
