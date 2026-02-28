from pymongo import MongoClient
import pandas as pd

MONGO_URL = "mongodb+srv://mandlachethan26_db_user:OVUltuvRiJgOz0EV@cluster0.2ulekqp.mongodb.net/?retryWrites=true&w=majority"

client = MongoClient(MONGO_URL)
client.admin.command("ping")
print("✅ Connected to MongoDB Atlas!")

db = client["hackathon_db"]
orders_col = db["dataset1"]

# Clear old data
orders_col.delete_many({})
print("🗑️ Old orders cleared")

# 🔥 Skip first 4 rows completely (title + empty rows)
orders_df = pd.read_excel("dataset1.xlsx", skiprows=4)

# Manually assign correct column names
orders_df.columns = [
    "Patient ID",
    "Patient Age",
    "Patient Gender",
    "Purchase Date",
    "Product Name",
    "Quantity",
    "Total Price (EUR)",
    "Dosage Frequency",
    "Extra"
]

# Drop extra column if not needed
orders_df = orders_df.drop(columns=["Extra"], errors="ignore")

# Remove completely empty rows
orders_df = orders_df.dropna(how="all")

print("Detected Columns:", orders_df.columns.tolist())

orders_col.insert_many(orders_df.to_dict("records"))

print("🔥 Orders uploaded successfully!")