from __future__ import annotations
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import init_db, save_prices_to_db
from src.app_state import get_app_context
from src.inference import run_batch_inference, load_artifacts

def simulate_wfp_api_fetch():
    """Simulate fetching the latest prices from WFP API."""
    print("📡 Fetching latest data from WFP VAM API...")
    
    # Create mock data for the last 7 days
    dates = [datetime.now() - timedelta(days=i) for i in range(7)]
    commodities = ["Maize", "Beans", "Rice", "Tomatoes"]
    counties = ["Nairobi", "Mombasa", "Kisumu", "Nakuru"]
    
    data = []
    for d in dates:
        for c in commodities:
            for co in counties:
                data.append({
                    "date": d,
                    "commodity": c,
                    "county": co,
                    "market": f"{co} Central Market",
                    "price_real": np.random.uniform(50, 150),
                    "record_type": "live"
                })
    
    return pd.DataFrame(data)

def main():
    # Initialize DB
    init_db()
    
    # 1. Fetch
    new_data = simulate_wfp_api_fetch()
    
    # 2. Run Inference
    print("🧠 Running anomaly detection inference...")
    try:
        # Load real artifacts
        bundle = load_artifacts()
        
        # Prepare minimal features for live scoring
        # Note: In production, we would join with historical lags here.
        # For this demonstration, we'll ensure columns match the model expectations.
        scored_data = run_batch_inference(new_data, bundle)
        
        # Mapping model outputs to DB columns
        if "prob_anomaly" in scored_data.columns:
            new_data["risk_score"] = scored_data["prob_anomaly"]
            new_data["is_anomaly"] = scored_data["pred_anomaly"]
        else:
            # Fallback if model is not loaded
            new_data["risk_score"] = 0.05
            new_data["is_anomaly"] = 0
            
    except Exception as e:
        print(f"⚠️ Inference warning: {e}. Using baseline scores.")
        new_data["risk_score"] = 0.1
        new_data["is_anomaly"] = 0

    new_data["severity"] = np.select(
        [new_data["risk_score"] >= 0.75, new_data["risk_score"] >= 0.40],
        ["High", "Medium"],
        default="Low"
    )
    
    # 3. Save to DB
    print(f"💾 Saving {len(new_data)} records to database...")
    save_prices_to_db(new_data)
    print("✅ Ingestion complete.")

if __name__ == "__main__":
    main()
