import requests
import json
from datetime import datetime

# 1. Configuration
# Default to local; replace with your Cloud Run URL if testing live
API_URL = "http://127.0.0.1:8000/v1/score"

# 2. Mock Price Record (WFP Format)
payload = {
    "records": [
        {
            "date": "01/01/2024", # Use a date within historical reference range
            "admin1": "Nairobi",
            "admin2": "Nairobi",
            "market": "Nairobi Central",
            "market_id": 1,
            "latitude": -1.2833,
            "longitude": 36.8167,
            "category": "cereals and tubers",
            "commodity": "Maize",
            "commodity_id": 1,
            "unit": "KG",
            "priceflag": "actual",
            "pricetype": "Retail",
            "currency": "KES",
            "price": 185.5,
            "usdprice": 1.2
        }
    ]
}

def test_scoring_engine():
    print(f"🚀 Sending test record to Intelligence Engine at {API_URL}...")
    try:
        response = requests.post(API_URL, json=payload, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        summary = result.get("summary", {})
        results = result.get("results", [])
        
        if not results:
            print("⚠️ No results returned from API.")
            return

        score = summary.get("avg_prob", 0)
        is_anomaly = results[0].get("pred_anomaly", 0)
        
        print("-" * 30)
        print("✅ Connection Successful!")
        print(f"📦 Input Price: KES {payload['records'][0]['price']}/kg")
        print(f"📈 Anomaly Probability: {score:.4f}")
        print(f"🚨 Prediction: {'ANOMALY DETECTED' if is_anomaly else 'Normal Price'}")
        print("-" * 30)
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to API. Ensure you've run: uvicorn api.main:app --port 8000")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_scoring_engine()
