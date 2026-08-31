import urllib.request
import json
import time

time.sleep(2)

def get(url):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())

print("=== FINCTRL AI PHASE 10 DEMO CASH FORECAST ===\n")
res = get("http://127.0.0.1:8000/api/forecast/cash?horizon_days=7&lookback_days=30&scenario=BASELINE")

print(f"Forecast ID: {res['forecast_id']}")
print(f"As Of Date: {res['as_of']}")
print(f"Scenario: {res['scenario']}")
print(f"Confidence Score: {res['confidence']}")
print(f"Data Quality Score: {res['data_quality']['score']}")
print("\nHistorical Summary (Lookback 30 Days):")
print(f"  Start: {res['historical']['start_date']} | End: {res['historical']['end_date']}")
print(f"  Historical Inflow:  INR {res['historical']['inflow']:,.2f}")
print(f"  Historical Outflow: INR {res['historical']['outflow']:,.2f}")
print(f"  Historical Net:     INR {res['historical']['net']:,.2f}")

print("\nForecast Summary (Horizon 7 Days):")
print(f"  Start: {res['forecast']['start_date']} | End: {res['forecast']['end_date']}")
print(f"  Forecast Inflow:  INR {res['forecast']['inflow']:,.2f}")
print(f"  Forecast Outflow: INR {res['forecast']['outflow']:,.2f}")
print(f"  Forecast Net:     INR {res['forecast']['net']:,.2f}")

print("\nDaily Projections:")
for item in res['daily_forecasts']:
    print(f"  [{item['date']}] Inflow: {item['expected_inflow']:,.2f} | Outflow: {item['expected_outflow']:,.2f} | Net: {item['expected_net']:,.2f} | Bounds: [{item['lower_bound']:,.2f}, {item['upper_bound']:,.2f}]")

print("\nUncertainty Metrics:")
print(f"  Method: {res['uncertainty']['method']}")
print(f"  Standard Deviation: INR {res['uncertainty']['std_dev']:,.2f}")
print(f"  Margin of Error:     INR {res['uncertainty']['margin_of_error']:,.2f}")

print("\nRisk Factors:")
for rf in res['risk_factors'][:5]:
    print(f"  - {rf}")

print("\nExplanation:")
print(f"  {res['explanation']}")
