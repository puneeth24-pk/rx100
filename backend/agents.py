import os
import json
import datetime
from typing import List, Optional, Dict, Any
from groq import Groq
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv
from langsmith import traceable
load_dotenv()

# Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME", "hackathon_db")

client = MongoClient(MONGO_URL)
db = client[DB_NAME]
inventory_col = db["dataset2"]  # Inventory (from previous context)
orders_col = db["connected_orders"]
traces_col = db["agent_traces"]
users_col = db["users"]

groq_client = Groq(api_key=GROQ_API_KEY)

class BaseAgent:
    def __init__(self, name: str):
        self.agent_name = name

    def log_trace(self, session_id: str, input_data: Any, reasoning: str, decision: str, output_data: Any):
        trace_doc = {
            "session_id": session_id,
            "agent_name": self.agent_name,
            "timestamp": datetime.datetime.utcnow(),
            "input": input_data,
            "reasoning": reasoning,
            "decision": decision,
            "output": output_data
        }
        traces_col.insert_one(trace_doc)
        print(f"[{self.agent_name}] {reasoning} -> {decision}")
        return trace_doc

class OrderingAgent(BaseAgent):
    def __init__(self):
        super().__init__("Conversational Ordering Agent")

    @traceable(name="OrderingAgent")
    def run(self, session_id: str, text: str) -> Dict[str, Any]:
        prompt = f"""
        You are a Pharmacy Ordering AI. The user might speak in English, Hindi, Telugu, or a mix of these.
        Extract order details from the user's text.
        Text: "{text}"
        
        Return ONLY valid JSON with:
        {{
            "medicine_name": "string",
            "quantity": number,
            "dosage_frequency": "string",
            "detected_language": "string",
            "symptom": "string"
        }}
        If details are missing, make a best guess or use null. Ensure the medicine name is translated/normalized to English if spoken in another language.
        """
        
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        # Extract JSON from potential markdown blocks
        content = completion.choices[0].message.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        try:
            output = json.loads(content)
        except json.JSONDecodeError:
            # Fallback for messy output
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                output = json.loads(json_match.group(0))
            else:
                output = {"medicine_name": None, "quantity": 1, "dosage_frequency": "As directed"}

        self.log_trace(session_id, text, "Extracted structured data from natural text using Llama 3.3.", "Extracted", output)
        return output

class SafetyAgent(BaseAgent):
    def __init__(self):
        super().__init__("Safety & Policy Agent")

    @traceable(name="SafetyAgent")
    def run(self, session_id: str, order_data: Dict[str, Any], prescription_data: Optional[str] = None) -> Dict[str, Any]:
        try:
            medicine_name = order_data.get("medicine_name")
            symptom = order_data.get("symptom")

            product = None
            if medicine_name:
                # Substring scan
                for item in inventory_col.find():
                    if medicine_name.lower() in item.get("product name", "").lower():
                        product = item
                        break
            
            # Symptom Fallback Logic: Ask LLM to pick the best product for the symptom
            if not product and symptom:
                print(f"DEBUG: Using Expert LLM to match symptom '{symptom}' to inventory...")
                # Fetch a sample of inventory to help the LLM decide
                sample_products = list(inventory_col.find({}, {"product name": 1, "medication description": 1, "indications": 1}).limit(20))
                
                prompt = f"""
                As an Expert Pharmacist, match the user's symptom to the best medicine in our inventory.
                Symptom: "{symptom}"
                Available Products: {json.dumps(sample_products, default=str)}
                
                Return ONLY the exact "product name" of the best match, or "None" if no good match exists.
                """
                completion = groq_client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt}]
                )
                match_name = completion.choices[0].message.content.strip().strip('"')
                
                if match_name and match_name != "None":
                    product = inventory_col.find_one({"product name": match_name})
                    if product:
                        medicine_name = match_name
                        print(f"DEBUG: LLM Found diagnostic match: {medicine_name}")

            if not medicine_name and not product:
                 return {"approved": False, "reason": "I couldn't identify a specific medicine. Could you please tell me which one you usually take, or describe your symptoms more specifically?", "procurement_available": False}
            
            if not product:
                reasoning = f"Medicine '{medicine_name}' not found locally."
                result = {"approved": False, "reason": reasoning, "procurement_available": True}
            elif product.get("stock", 0) <= 0:
                reasoning = f"Medicine '{medicine_name}' is out of stock locally."
                result = {"approved": False, "reason": reasoning, "procurement_available": True}
            elif product.get("prescription_required") == "Yes":
                if prescription_data:
                    reasoning = f"Validating prescription for '{medicine_name}'."
                    # Autonomous LLM Validation
                    prompt = f"""
                    You are a strict Pharmacy AI. The user is ordering '{medicine_name}'.
                    They have provided the following prescription text:
                    "{prescription_data}"
                    
                    Does this prescription validly cover or mention '{medicine_name}' or a direct medical synonym/symptom for it?
                    Return ONLY a JSON object:
                    {{
                        "is_valid": boolean,
                        "explanation": "string explaining why it is valid or invalid"
                    }}
                    """
                    completion = groq_client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=[{"role": "user", "content": prompt}],
                        response_format={"type": "json_object"}
                    )
                    validation = json.loads(completion.choices[0].message.content)
                    
                    if validation.get("is_valid"):
                        reasoning = f"Prescription validated: {validation.get('explanation')}"
                        result = {"approved": True, "product": product}
                    else:
                        reasoning = f"Prescription rejected: {validation.get('explanation')}"
                        result = {"approved": False, "reason": f"I cannot approve this order based on the provided prescription. {validation.get('explanation')}"}
                else:
                    reasoning = f"Medicine '{medicine_name}' requires a prescription."
                    result = {"approved": False, "reason": reasoning, "prescription_needed": True}
            else:
                reasoning = f"Medicine '{medicine_name}' is available locally without a prescription."
                result = {"approved": True, "product": product}
        except Exception as e:
            print(f"Safety Check Error: {e}")
            result = {"approved": False, "reason": "Expert suggestion: Not found in inventory.", "procurement_available": True}
            reasoning = "Fallback due to system error"
            
        self.log_trace(session_id, {"order": order_data, "prescription": prescription_data}, reasoning, "Decision Made", result)
        return result

class RefillAgent(BaseAgent):
    def __init__(self):
        super().__init__("Predictive Refill Agent")

    @traceable(name="RefillAgent")
    def run(self, session_id: str, patient_id: str) -> List[Dict[str, Any]]:
        # Fetch last orders for patient
        history = list(orders_col.find({"patient.id": patient_id}).sort("purchase_date", -1).limit(5))
        
        alerts = []
        if not history:
            self.log_trace(session_id, patient_id, "No past orders found for this user.", "Skipped Analysis", alerts)
            return alerts

        for order in history:
            # Simple logic: if dosage is "twice a day" and qty is 30, it lasts 15 days.
            # We'll use LLM to estimate refill need based on history.
            prompt = f"""
            Analyze this pharmacy order history and determine if a refill is needed soon.
            Order: {json.dumps(order, default=str)}
            Current Date: {datetime.date.today()}
            
            Return JSON:
            {{
                "needs_refill": boolean,
                "days_until_refill": number,
                "reason": "string"
            }}
            """
            completion = groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            analysis = json.loads(completion.choices[0].message.content)
            if analysis["needs_refill"]:
                alerts.append({
                    "medicine": order.get("product", {}).get("name"),
                    "days": analysis["days_until_refill"],
                    "reason": f"Proactive check: {analysis['reason']}"
                })
        
        self.log_trace(session_id, patient_id, f"Expert Refill Analysis: Found {len(alerts)} items requiring attention soon.", "Analysis Complete", alerts)
        
        if alerts:
            # Check if user has an email on file
            from emailer import send_refill_email
            db_user = users_col.find_one({"patient_id": patient_id})
            if db_user and db_user.get("email"):
                print(f"DEBUG: Found email {db_user['email']} for patient {patient_id}. Sending alerts...")
                send_refill_email(db_user["email"], db_user.get("username", "Valued Patient"), alerts)
            else:
                print(f"DEBUG: No email found for patient {patient_id}. Skipping email alert.")
                
        return alerts

class ActionAgent(BaseAgent):
    def __init__(self):
        super().__init__("Action Agent")

    @traceable(name="ActionAgent")
    def run(self, session_id: str, patient_id: str, order_data: Dict[str, Any], product: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        # Handle external procurement case
        if not product:
            # Trigger external warehouse webhook (mock)
            result = {"status": "Procurement Triggered", "source": "Partner Shop"}
            self.log_trace(session_id, order_data, f"Medicine '{order_data.get('medicine_name')}' not found locally. Triggered external procurement.", "External Success", result)
            return result

        # 1. Insert order locally
        merged_doc = {
            "patient": {"id": patient_id},
            "purchase_date": datetime.datetime.utcnow().isoformat(),
            "product": {
                "product_id": product.get("product id"),
                "name": product.get("product name"),
                "price": product.get("price rec")
            },
            "quantity": order_data.get("quantity", 1),
            "total_price": float(product.get("price rec", 0)) * order_data.get("quantity", 1),
            "dosage_frequency": order_data.get("dosage_frequency")
        }
        orders_col.insert_one(merged_doc)
        
        # 2. Decrease stock
        inventory_col.update_one(
            {"_id": product["_id"]},
            {"$inc": {"stock": -(order_data.get("quantity", 1))}}
        )
        
        # 3. Trigger Mock Webhook
        webhook_res = {"status": "success", "webhook_url": "https://webhook.site/mock-pharmacy-action"}
        
        result = {"status": "Order Processed", "order_id": str(merged_doc.get("_id"))}
        self.log_trace(session_id, order_data, "Executed DB updates and triggered webhook.", "Success", result)
        return result

class Orchestrator:
    def __init__(self):
        self.ordering = OrderingAgent()
        self.safety = SafetyAgent()
        self.refill = RefillAgent()
        self.action = ActionAgent()

    @traceable(name="Medicine Order Process")
    def process_chat_order(self, session_id: str, patient_id: str, text: str, prescription_data: Optional[str] = None) -> Dict[str, Any]:
        try:
            # 1. Extraction
            order_details = self.ordering.run(session_id, text)
            
            # 2. Safety & Policy
            safety_result = self.safety.run(session_id, order_details, prescription_data)
            
            # 1.5 Fetch traces safely
            try:
                internal_traces = list(traces_col.find({"session_id": session_id}).sort("timestamp", 1))
                for t in internal_traces: t["_id"] = str(t["_id"])
            except:
                internal_traces = []

            if not safety_result["approved"]:
                med_name = order_details.get("medicine_name") or "this item"
                if safety_result.get("procurement_available"):
                    msg = f"We don't have '{med_name}' in our local inventory at the moment. However, as your expert pharmacist, I can procure it for you from one of our partner shops! Shall I proceed with the external order?"
                elif safety_result.get("prescription_needed"):
                    msg = f"I've found '{med_name}', but it requires a prescription which I don't see on file. Please upload it to continue."
                else:
                    msg = safety_result["reason"]
                
                return {
                    "success": False,
                    "message": msg,
                    "traces": internal_traces
                }
            
            # 3. Fulfillment (If approved)
            action_result = self.action.run(session_id, patient_id, order_details, safety_result.get("product"))
            
            # 4. Refill Check
            refill_alerts = self.refill.run(session_id, patient_id)
            
            final_result = {
                "success": True,
                "message": f"✅ Available! Order placed successfully for {order_details.get('medicine_name', 'your medicine')}.",
                "order": order_details,
                "refill_alerts": refill_alerts,
                "action": action_result,
                "traces": internal_traces
            }
            return final_result
        except Exception as e:
            print(f"Orchestrator Error: {e}")
            import traceback
            print(traceback.format_exc())
            return {
                "success": False,
                "message": "I encountered an issue processing your order. However, if the item is unavailable, I can usually procure it from a partner shop. Please try again or specify the medicine more clearly.",
                "traces": []
            }
