import os
import subprocess

os.environ["BUCKET_SERVICE_URL"] = "http://127.0.0.1:8001"
subprocess.run(["venv\\Scripts\\python.exe", "-m", "uvicorn", "app.main:app", "--port", "8000"])
