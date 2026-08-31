import urllib.request
import json
import time

time.sleep(3)

def get(url):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())

print("=== FINCTRL AI PHASE 11 DEMO — TAX LINE MATCHING ===\n")

# Single invoice demo
print("--- SINGLE INVOICE MATCH: INV-00001 ---")
res = get("http://127.0.0.1:8000/api/tax-matching/INV-00001")
print(f"Match ID:        {res['match_id']}")
print(f"Invoice ID:      {res['invoice_id']}")
print(f"Tax Record ID:   {res['tax_id']}")
print(f"Status:          {res['status']}")
print(f"Reason Code:     {res['reason_code']}")
print(f"Confidence:      {res['confidence']}")
print(f"Needs Review:    {res['needs_review']}")
print(f"\nInvoice Tax:     INR {res['invoice_tax_amount']}")
print(f"Ledger Tax:      INR {res['ledger_tax_amount']}")
print(f"Invoice Rate:    {res['invoice_tax_rate']*100:.2f}%")
print(f"Ledger Rate:     {res['ledger_tax_rate']*100:.2f}%")
print(f"Taxable Amount:  INR {res['invoice_taxable_amount']}")
print(f"Expected Tax:    INR {res['expected_tax_amount']}")
print(f"Difference:      INR {res['difference']:.2f}")
print("\nEvidence:")
for e in res['evidence']:
    print(f"  [{e['source']}:{e['entity_id']}] {e['field']} = {e['value']}")
print("\nRule Evaluations:")
for r in res['rule_evaluations']:
    print(f"  [{r['status']}] {r['rule_name']}: Expected={r['expected_val']} Actual={r['actual_val']} Diff={r['difference']}")
print(f"\nExplanation: {res['explanation']}")

# Batch demo
print("\n\n--- BATCH TAX MATCHING (ALL INVOICES) ---")
batch = get("http://127.0.0.1:8000/api/tax-matching")
print(f"Total Invoices Checked:    {batch['total_invoices_checked']}")
print(f"Exact Matches:             {batch['exact_matches']}")
print(f"Amount Mismatches:         {batch['amount_mismatches']}")
print(f"Rate Mismatches:           {batch['rate_mismatches']}")
print(f"Taxable Amount Mismatches: {batch['taxable_amount_mismatches']}")
print(f"Calculation Mismatches:    {batch['calculation_mismatches']}")
print(f"Missing Tax Records:       {batch['missing_records']}")
print(f"Duplicate Tax Records:     {batch['duplicate_records']}")
print(f"\nStatus Breakdown:")
for r in batch['results']:
    print(f"  {r['invoice_id']:12s} | {r['status']:30s} | {r['reason_code']}")
