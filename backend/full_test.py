import requests
import os
import sys
from dotenv import load_dotenv
load_dotenv()

BASE = "http://localhost:8002"
results = []

def log(msg):
    print(msg)
    results.append(msg)

log("=" * 50)
log("RxGenie Full System Test")
log("=" * 50)

# 1. Register
log("\n[1] REGISTER new user...")
try:
    r = requests.post(f"{BASE}/auth/register", json={"username": "test_agent_user", "password": "test123"}, timeout=10)
    log(f"  Status: {r.status_code}")
    log(f"  Body: {r.text[:200]}")
except Exception as e:
    log(f"  ERROR: {e}")

# 2. Login
log("\n[2] LOGIN...")
try:
    r = requests.post(f"{BASE}/auth/login", json={"username": "test_agent_user", "password": "test123"}, timeout=10)
    log(f"  Status: {r.status_code}")
    log(f"  Body: {r.text[:200]}")
    user_data = r.json().get("user", {})
    patient_id = user_data.get("patient_id", "PAT_TEST001")
    log(f"  patient_id: {patient_id}")
except Exception as e:
    log(f"  ERROR: {e}")
    patient_id = "PAT_TEST001"

# 3. Low stock
log("\n[3] LOW STOCK inventory...")
try:
    r = requests.get(f"{BASE}/admin/low-stock", timeout=10)
    items = r.json()
    log(f"  Status: {r.status_code} | Count: {len(items)}")
    for item in items[:3]:
        log(f"  - {item.get('product name')} stock={item.get('stock')}")
except Exception as e:
    log(f"  ERROR: {e}")

# 4. Chat Order
log("\n[4] CHAT ORDER (Paracetamol)...")
log("  Agents: OrderingAgent -> SafetyAgent -> ActionAgent -> RefillAgent")
try:
    r = requests.post(f"{BASE}/chat-order", 
        json={"patient_id": patient_id, "text": "I need Paracetamol for fever"}, 
        timeout=45)
    d = r.json()
    log(f"  Status: {r.status_code}")
    log(f"  success: {d.get('success')}")
    log(f"  message: {str(d.get('message', ''))[:100]}")
    log(f"  action: {d.get('action')}")
    log(f"  traces_returned: {len(d.get('traces', []))}")
    log(f"  refill_alerts: {len(d.get('refill_alerts', []))}")
except Exception as e:
    log(f"  ERROR: {e}")

# 5. Orders in DB
log(f"\n[5] ORDERS in MongoDB for patient...")
try:
    r = requests.get(f"{BASE}/orders?patient_id={patient_id}", timeout=10)
    orders = r.json()
    log(f"  Status: {r.status_code} | Total orders: {len(orders)}")
    for o in orders[:3]:
        log(f"  - {o.get('product',{}).get('name')} qty={o.get('quantity')} date={str(o.get('purchase_date',''))[:10]}")
except Exception as e:
    log(f"  ERROR: {e}")

# 6. Agent Traces in DB
log("\n[6] AGENT TRACES in MongoDB...")
try:
    r = requests.get(f"{BASE}/admin/traces", timeout=10)
    traces = r.json()
    log(f"  Status: {r.status_code} | Total traces: {len(traces)}")
    for t in traces[:5]:
        log(f"  - Agent: {t.get('agent_name')} | Decision: {t.get('decision')} | Time: {str(t.get('timestamp',''))[:19]}")
except Exception as e:
    log(f"  ERROR: {e}")

# 7. Refill alerts
log(f"\n[7] REFILL ALERTS...")
try:
    r = requests.get(f"{BASE}/admin/refills?patient_id={patient_id}", timeout=20)
    alerts = r.json()
    log(f"  Status: {r.status_code} | Alerts: {len(alerts)}")
    for a in alerts[:2]:
        log(f"  - {str(a.get('reason',''))[:80]}")
except Exception as e:
    log(f"  ERROR: {e}")

# 8. LangSmith
log("\n[8] LANGSMITH CHECK...")
ls_key = os.getenv("LANGSMITH_API_KEY", "")
ls_proj = os.getenv("LANGSMITH_PROJECT", "")
ls_tracing = os.getenv("LANGSMITH_TRACING", "false")
log(f"  TRACING={ls_tracing} | PROJECT={ls_proj}")
log(f"  KEY={ls_key[:25]}...")
try:
    r = requests.get(
        f"https://api.smith.langchain.com/api/v1/runs?project_name={ls_proj}&limit=5",
        headers={"x-api-key": ls_key},
        timeout=15
    )
    log(f"  LangSmith API status: {r.status_code}")
    if r.status_code == 200:
        runs = r.json()
        log(f"  RUNS FOUND: {len(runs)}")
        for run in runs[:3]:
            log(f"  - name={run.get('name')} status={run.get('status')}")
    else:
        log(f"  Response: {r.text[:300]}")
except Exception as e:
    log(f"  ERROR: {e}")

log("\n" + "=" * 50)
log("TEST DONE")
log("=" * 50)
