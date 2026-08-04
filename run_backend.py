import os
import subprocess

# Live Real-Time Deployed Environment Variables for Demo
os.environ["BUCKET_SERVICE_URL"] = "https://bhiv-bucket-i1l6.onrender.com"
os.environ["DGIC_SERVICE_URL"] = "https://dgic-3lah.onrender.com"
os.environ["INSIGHTBRIDGE_URL"] = "https://bhiv-6.onrender.com"

print("=======================================================================")
print("🚀 BOOTING SŪTRADHĀRA CONTROL PLANE (LIVE DEMO MODE)")
print(f"🔗 Attached to Live Bucket       : {os.environ['BUCKET_SERVICE_URL']}")
print(f"🔗 Attached to Live DGIC         : {os.environ['DGIC_SERVICE_URL']}")
print(f"🔗 Attached to Live InsightBridge: {os.environ['INSIGHTBRIDGE_URL']}")
print("=======================================================================\n")

subprocess.run(["venv\\Scripts\\python.exe", "-m", "uvicorn", "app.main:app", "--port", "8000"])
