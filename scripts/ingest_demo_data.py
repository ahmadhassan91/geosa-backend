#!/usr/bin/env python3
"""
Ingest Demo Data Script

Uploads the manually downloaded GEBCO file and starts an analysis run.
"""

import os
import sys
import time
import requests
from pathlib import Path

API_URL = "http://localhost:8000/api/v1"
DEMO_FILE = Path("/Users/clustox_1/Documents/GeoSA/hydroq-qc-assistant/data/samples/gebco_2025_n28.0_s25.0_w48.0_e51.0.tif")

def main():
    print(f"🌊 HydroQ Demo Ingestion")
    print(f"   Target: {DEMO_FILE}")

    if not DEMO_FILE.exists():
        print(f"❌ File not found: {DEMO_FILE}")
        return

    # 1. Login (or register if needed)
    username = "demo_user"
    password = "DemoUser123!"
    
    print("\n🔐 Authenticating...")
    
    # Try login first
    login_data = {"username": username, "password": password}
    response = requests.post(f"{API_URL}/auth/login", json=login_data)
    
    if response.status_code == 401:
        print("   User not found, registering...")
        # Register
        reg_data = {
            "username": username,
            "email": "demo@example.com",
            "password": password,
            "role": "admin"
        }
        reg_resp = requests.post(f"{API_URL}/auth/register", json=reg_data)
        if reg_resp.status_code != 201:
            print(f"❌ Registration failed: {reg_resp.text}")
            return
        # Login again
        response = requests.post(f"{API_URL}/auth/login", json=login_data)

    if response.status_code != 200:
        print(f"❌ Login failed: {response.text}")
        return

    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Authenticated")

    # 2. Upload Dataset
    print("\nCcUploading dataset...")
    with open(DEMO_FILE, "rb") as f:
        files = {"file": (DEMO_FILE.name, f, "image/tiff")}
        data = {
            "name": "Monterey Canyon Sample",
            "description": "GEBCO 2025 Grid - Monterey Canyon region"
        }
        response = requests.post(f"{API_URL}/datasets/", headers=headers, files=files, data=data)

    if response.status_code not in (200, 201):
        print(f"❌ Upload failed: {response.text}")
        return

    dataset = response.json()
    dataset_id = dataset["id"]
    print(f"✅ Uploaded dataset: {dataset['name']} (ID: {dataset_id})")

    # 3. Start Analysis
    print("\n🧠 Starting analysis...")
    run_data = {
        "dataset_id": dataset_id,
        "name": "Initial Scan",
        "configuration": {"anomaly_detection": {"isolation_forest": {"contamination": 0.05}}}
    }
    response = requests.post(f"{API_URL}/runs/", headers=headers, json=run_data)

    if response.status_code not in (200, 201):
        print(f"❌ Run start failed: {response.text}")
        return

    run = response.json()
    run_id = run["id"]
    print(f"✅ Run started (ID: {run_id})")

    # 4. Poll for completion
    print("\n⏳ Waiting for completion...")
    while True:
        response = requests.get(f"{API_URL}/runs/{run_id}/status", headers=headers)
        status = response.json()
        
        state = status["status"]
        progress = status.get("progress", 0)
        
        sys.stdout.write(f"\r   Status: {state} ({progress}%)")
        sys.stdout.flush()
        
        if state in ["completed", "failed"]:
            print("")
            break
        
        time.sleep(1)

    if state == "completed":
        print("\n🎉 Analysis Complete!")
        # Get anomaly count
        response = requests.get(f"{API_URL}/runs/{run_id}/anomalies", headers=headers)
        anomalies = response.json()
        count = len(anomalies["items"])
        print(f"   Found {count} anomalies")
        print(f"\n👉 View results at: http://localhost:5173/analysis/{run_id}")
    else:
        print("\n❌ Analysis Failed")

if __name__ == "__main__":
    main()
