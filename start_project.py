import subprocess
import webbrowser
import time
import sys
import urllib.request
from urllib.error import URLError

def wait_for_server(url: str, timeout: int = 15) -> bool:
    """Wait until the server is responsive or timeout is reached."""
    start_time = time.time()
    print(f"[*] Waiting for backend server to start at {url}...")
    while time.time() - start_time < timeout:
        try:
            urllib.request.urlopen(url)
            return True
        except URLError:
            time.sleep(0.5)
    return False

def main():
    print("=" * 60)
    print(" [*] SOVEREIGN CORE: LAUNCHING BACKEND & FRONTEND")
    print("=" * 60)

    # Command to start the FastAPI server
    cmd = [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8000", "--reload"]
    
    try:
        # Start the backend as a subprocess
        print("[>] Starting FastAPI server on port 8000...")
        backend_process = subprocess.Popen(cmd)
        
        # Check if the server is up
        health_url = "http://localhost:8000/health"
        if wait_for_server(health_url):
            panel_url = "http://localhost:8000/panel"
            print(f"\n[+] Server is up! Launching Control Panel UI in your browser...")
            print(f"[*] URL: {panel_url}")
            # Open the Sovereign Core Control Panel in the default web browser
            webbrowser.open(panel_url)
        else:
            print("\n[-] Error: Backend server did not start in time. Check the logs above.")
        
        # Keep the script running to keep the subprocess alive
        print("\n[*] Press Ctrl+C to stop the server and exit.")
        backend_process.wait()

    except KeyboardInterrupt:
        print("\n[!] Shutting down Sovereign Core...")
        backend_process.terminate()
        backend_process.wait()
        print("[*] Shutdown complete.")

if __name__ == "__main__":
    main()
