from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()
client = MongoClient(os.getenv("MONGO_URL"))

print("Listing all databases and collections:")
for db_name in client.list_database_names():
    print(f"\nDatabase: {db_name}")
    db = client[db_name]
    print(f"Collections: {db.list_collection_names()}")
    if "connected_orders" in db.list_collection_names():
        print(f"!!! FOUND connected_orders in {db_name} !!!")
        for doc in db["connected_orders"].find().limit(2):
            print(doc)
