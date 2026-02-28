from pymongo import MongoClient

# ⚠️ After hackathon change password
MONGO_URL = "mongodb+srv://mandlachethan26_db_user:OVUltuvRiJgOz0EV@cluster0.2ulekqp.mongodb.net/?retryWrites=true&w=majority"

client = MongoClient(MONGO_URL)
client.admin.command("ping")
print("✅ Connected to MongoDB Atlas!")

db = client["hackathon_db"]

# Correct collections
inventory_col = db["dataset2"]   # Inventory
orders_col = db["dataset1"]      # Orders
connected_col = db["connected_orders"]

# Clear old merged data
connected_col.delete_many({})
print("🗑️ Old connected data cleared")

orders_data = list(orders_col.find())
inserted_count = 0

for order in orders_data:
    product_name = str(order.get("Product Name", "")).strip()

    # Case-insensitive exact match
    product = inventory_col.find_one({
        "product name": {"$regex": f"^{product_name}$", "$options": "i"}
    })

    if product:
        merged_doc = {
            "patient": {
                "id": order.get("Patient ID"),
                "age": order.get("Patient Age"),
                "gender": order.get("Patient Gender")
            },
            "purchase_date": order.get("Purchase Date"),
            "product": {
                "product_id": product.get("product id"),
                "name": product.get("product name"),
                "pzn": product.get("pzn"),
                "price": product.get("price rec"),
                "package_size": product.get("package size"),
                "description": product.get("descriptions")
            },
            "quantity": order.get("Quantity"),
            "total_price": order.get("Total Price (EUR)"),
            "dosage_frequency": order.get("Dosage Frequency")
        }

        connected_col.insert_one(merged_doc)
        inserted_count += 1

print(f"\n🔥 DONE! Inserted {inserted_count} connected records.")