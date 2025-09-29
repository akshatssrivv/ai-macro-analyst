import os
import streamlit as st
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from dotenv import load_dotenv

# Load .env if running locally
load_dotenv()

def _get_secret(name, default=None):
    # Prefer Streamlit secrets on Cloud; fallback to env for local dev
    if "secrets" in dir(st) and name in st.secrets:
        return st.secrets[name]
    return os.getenv(name, default)

MONGO_URI = _get_secret("MONGO_URI", "mongodb://localhost:27017")
DB_NAME   = _get_secret("DB_NAME", "macro-agent")

# Short timeouts so failures fail fast and show a clear message
client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=5000,
    socketTimeoutMS=5000,
)

# Health check on import (gives you a friendly error in the UI)
try:
    client.admin.command("ping")
except ServerSelectionTimeoutError as e:
    raise RuntimeError(
        "Cannot connect to MongoDB. Check MONGO_URI / networking / credentials."
    ) from e

db = client[DB_NAME]

def get_collection(name: str):
    return db[name]
