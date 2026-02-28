import requests
import json
import time

BASE = 'http://localhost:8002'

def test_snapshot():
    print("Testing /admin/database-snapshot...")
    try:
        r = requests.get(f'{BASE}/admin/database-snapshot', timeout=5)
        if r.status_code == 200:
            data = r.json()
            print(f"✅ SUCCESS: Database Snapshot retrieved. Orders: {len(data.get('orders', []))}, Inventory: {len(data.get('inventory', []))}")
            return True
        else:
            print(f"❌ FAILED: Snapshot returned {r.status_code}")
            return False
    except Exception as e:
        print(f"❌ ERROR: Could not connect to backend: {e}")
        return False

def test_chat_order():
    print("Testing /chat-order (Autonomous Prescription Validation)...")
    try:
        payload = {
            'patient_id': 'test_expert_1',
            'text': 'I need some Aqualibra',
            'prescription_data': 'Patient is prescribed Aqualibra for chronic condition. - Dr. Gregory House'
        }
        r = requests.post(f'{BASE}/chat-order', json=payload, timeout=30)
        if r.status_code == 200:
            data = r.json()
            msg = data.get('message', '') or data.get('response', '')
            print(f"✅ SUCCESS: Chat Order processed. AI Response: {msg[:120]}...")
            return True
        else:
            print(f"❌ FAILED: Chat Order returned {r.status_code}, {r.text}")
            return False
    except Exception as e:
        print(f"❌ ERROR: Chat Order failed: {e}")
        return False

if __name__ == '__main__':
    print("--- STARTING SYSTEM TEST ---")
    s1 = test_snapshot()
    s2 = test_chat_order()
    if s1 and s2:
        print("--- ALL BACKEND TESTS PASSED ---")
    else:
        print("--- SYSTEM TESTS FAILED ---")
