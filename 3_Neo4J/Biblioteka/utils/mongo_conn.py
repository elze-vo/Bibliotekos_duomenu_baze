from pymongo import MongoClient
from Biblioteka.config import MONGO_URI, DB_NAME

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

def get_mongo_db():
    return db
