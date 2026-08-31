import urllib.request
import json
import time

time.sleep(2)

def post(url, data):
    body = json.dumps(data).encode()
    headers = {'Content-Type': 'application/json'}
    req = urllib.request.Request(url, data=body, headers=headers, method='POST')
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())

demo_questions = [
    "What is the status of PAY-00001?",
    "How much was refunded for PAY-00001?",
    "Was PAY-00001 settled?",
    "What tax was recorded for INV-00001?",
    "Compare invoice tax and tax ledger tax for INV-00001.",
    "Why is CASE-00001 mismatched?",
    "How many reconciliation cases require investigation?",
    "What is the total payment amount?"
]

print("=== FINCTRL AI PHASE 9 DEMO QUESTIONS TEST ===\n")
for i, q in enumerate(demo_questions, 1):
    res = post("http://127.0.0.1:8000/api/finance/qa", {"question": q})
    print(f"Demo Q{i}: \"{q}\"")
    print(f"  Status: {res.get('status')}")
    print(f"  Answer: {res.get('answer')}")
    print(f"  Citations: {res.get('citations')}")
    print("-" * 60)
