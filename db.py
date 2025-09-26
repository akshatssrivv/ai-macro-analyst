import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "macro_agent")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

def get_collection(name: str):
    return db[name]

