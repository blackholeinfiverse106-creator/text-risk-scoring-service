import os

filepath = r"c:\blackhole\text-risk-scoring-service\app\main.py"

with open(filepath, "r", encoding="utf-8") as f:
    code = f.read()

# Add the endpoints to the end of the file
new_endpoints = """
# ============================================================
# Niyantran Kendra + Control Panel Integrations
# ============================================================

from fastapi.responses import HTMLResponse
from app.niyantran_streamer import get_recent_traces

@app.get("/api/v1/niyantran/traces")
def niyantran_traces():
    return get_recent_traces()

@app.get("/panel", response_class=HTMLResponse)
def control_panel():
    import os
    panel_path = os.path.join(os.path.dirname(__file__), "..", "ui", "control_panel.html")
    with open(panel_path, "r", encoding="utf-8") as f:
        return f.read()
"""

if "Niyantran Kendra" not in code:
    code += new_endpoints

with open(filepath, "w", encoding="utf-8") as f:
    f.write(code)

print("Main patched successfully.")
