from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from bson import ObjectId
from pydantic import BaseModel
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv
from agents import Orchestrator

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME", "hackathon_db")

client = MongoClient(MONGO_URL)
db = client[DB_NAME]
orders_col = db["connected_orders"]
inventory_col = db["dataset2"]
traces_col = db["agent_traces"]
users_col = db["users"]

orchestrator = Orchestrator()

# =============================
# Pydantic Models
# =============================

class User(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    patient_id: Optional[str] = None

class Patient(BaseModel):
    id: str
    age: int
    gender: str

class Medication(BaseModel):
    product_id: int
    name: str
    pzn: str
    price: float
    package_size: str
    medication_description: str

class Order(BaseModel):
    patient: Patient
    purchase_date: str
    product: Medication
    quantity: int
    total_price: float
    dosage_frequency: str

class ChatOrderRequest(BaseModel):
    patient_id: str
    text: str
    prescription_data: Optional[str] = None

# =============================
# Auth Endpoints
# =============================

@app.post("/auth/register")
async def register(user: User):
    if users_col.find_one({"username": user.username}):
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Generate a patient_id if not provided
    if not user.patient_id:
        oid_str = str(ObjectId())
        user.patient_id = f"PAT_{oid_str[:8].upper()}"
        
    users_col.insert_one(user.dict())
    user_dict = user.dict()
    if "_id" in user_dict:
        del user_dict["_id"]
    return {"message": "User registered successfully", "user": user_dict}

@app.post("/auth/login")
async def login(user: User):
    db_user = users_col.find_one({"username": user.username, "password": user.password})
    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    db_user["_id"] = str(db_user["_id"])
    return {"message": "Login successful", "user": db_user}

@app.post("/auth/update-email")
async def update_email(request: Dict[str, str]):
    username = request.get("username")
    new_email = request.get("email")
    if not username or not new_email:
        raise HTTPException(status_code=400, detail="Missing username or email")
    
    res = users_col.update_one({"username": username}, {"$set": {"email": new_email}})
    if res.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
        
    return {"message": "Email updated successfully"}

# =============================
# Agentic AI APIs
# =============================

@app.post("/chat-order")
async def chat_order(request: ChatOrderRequest):
    session_id = str(ObjectId())
    try:
        result = orchestrator.process_chat_order(session_id, request.patient_id, request.text, request.prescription_data)
        
        # Ensure result is JSON serializable (handle ObjectIds or complex types)
        def clean_data(obj):
            if isinstance(obj, list): return [clean_data(x) for x in obj]
            if isinstance(obj, dict): return {k: clean_data(v) for k, v in obj.items()}
            if isinstance(obj, ObjectId): return str(obj)
            return obj

        return clean_data(result)
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/traces")
async def get_traces(limit: int = 10):
    traces = list(traces_col.find().sort("timestamp", -1).limit(limit))
    for t in traces:
        t["_id"] = str(t["_id"])
    return traces

@app.get("/admin/low-stock")
async def get_low_stock(threshold: int = 5):
    items = list(inventory_col.find({"stock": {"$lt": threshold}}))
    for i in items:
        i["_id"] = str(i["_id"])
    return items

@app.get("/admin/refills")
async def get_refills(patient_id: str):
    session_id = str(ObjectId())
    alerts = orchestrator.refill.run(session_id, patient_id)
    return alerts

@app.get("/admin/database-snapshot")
async def get_database_snapshot():
    # Return limited raw snapshot of orders and inventory
    ords = list(orders_col.find().sort("purchase_date", -1).limit(50))
    inv = list(inventory_col.find().limit(100))
    
    for o in ords: o["_id"] = str(o["_id"])
    for i in inv: i["_id"] = str(i["_id"])
        
    return {"orders": ords, "inventory": inv}

@app.get("/health/email")
async def health_email():
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_user = os.getenv("SMTP_USERNAME")
    return {"live": bool(smtp_server and smtp_user)}

# =============================
# CRUD APIs (Preserved)
# =============================

@app.get("/orders")
def get_orders(patient_id: Optional[str] = None):
    query = {}
    if patient_id:
        query = {"patient.id": patient_id}
    data = list(orders_col.find(query).sort("purchase_date", -1))
    for item in data:
        item["_id"] = str(item["_id"])
    return data


@app.post("/orders")
def add_order(order: Order):
    orders_col.insert_one(order.dict())
    return {"message": "Order added successfully"}


@app.delete("/orders/{id}")
def delete_order(id: str):
    orders_col.delete_one({"_id": ObjectId(id)})
    return {"message": "Order deleted successfully"}


@app.put("/orders/{id}")
def update_order(id: str, updated_data: Order):
    orders_col.update_one(
        {"_id": ObjectId(id)},
        {"$set": updated_data.dict()}
    )
    return {"message": "Order updated successfully"}

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 8002))
    uvicorn.run(app, host="0.0.0.0", port=port)