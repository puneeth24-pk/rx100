from pymongo import MongoClient
import os
from dotenv import load_dotenv
import json

load_dotenv()
client = MongoClient(os.getenv('MONGO_URL'))
db = client[os.getenv('DB_NAME', 'hackathon_db')]
col = db['dataset2']

def check_inventory():
    print("Listing first 50 products:")
    docs = list(col.find({}, {"product name": 1, "indication": 1}).limit(50))
    for d in docs:
        print(f"- {d.get('product name')} ({d.get('indication')})")

    print("\nSearching for 'Paracetamol':")
    paracetamol_query = {"product name": {"$regex": "Paracetamol", "$options": "i"}}
    paracetamol_results = list(col.find(paracetamol_query))
    print(f"Found {len(paracetamol_results)} matches for Paracetamol:")
    for res in paracetamol_results:
        print(json.dumps(res, default=str, indent=4))

if __name__ == "__main__":
    check_inventory()
