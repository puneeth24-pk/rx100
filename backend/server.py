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

orchestrator = Orchestrator()

# =============================
# Pydantic Models
# =============================

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

# =============================
# Agentic AI APIs
# =============================

@app.post("/chat-order")
async def chat_order(request: ChatOrderRequest):
    session_id = str(ObjectId())
    try:
        result = orchestrator.process_chat_order(session_id, request.patient_id, request.text)
        return result
    except Exception as e:
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

# =============================
# CRUD APIs (Preserved)
# =============================

@app.get("/orders")
def get_orders():
    data = list(orders_col.find())
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