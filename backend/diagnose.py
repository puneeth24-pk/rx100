from pymongo import MongoClient
import os, json
from dotenv import load_dotenv
from bson import json_util

load_dotenv()
client = MongoClient(os.getenv("MONGO_URL"))

# List ALL databases and their collections
for dbname in client.list_database_names():
    db = client[dbname]
    cols = db.list_collection_names()
    print(f"\n=== DB: {dbname} | Collections: {cols}")
    for col in cols:
        count = db[col].count_documents({})
        print(f"   {col}: {count} docs")
        if count > 0:
            doc = db[col].find_one()
            print(f"   Sample keys: {list(doc.keys())}")
