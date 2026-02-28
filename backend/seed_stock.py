from pymongo import MongoClient
import os
import random
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.getenv('MONGO_URL'))
db = client[os.getenv('DB_NAME')]
col = db['dataset2']

def seed_missing_fields():
    print("Seeding stock and prescription_required fields...")
    all_docs = list(col.find())
    count = 0
    for doc in all_docs:
        update_data = {}
        if 'stock' not in doc:
            update_data['stock'] = random.randint(10, 50)
        if 'prescription_required' not in doc:
            # Most items don't need prescription (80% No, 20% Yes)
            update_data['prescription_required'] = "Yes" if random.random() < 0.2 else "No"
        
        if update_data:
            col.update_one({'_id': doc['_id']}, {'$set': update_data})
            count += 1
    
    print(f"Updated {count} documents.")

if __name__ == "__main__":
    seed_missing_fields()
