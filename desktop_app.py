# desktop_app.py
import threading
import time
import subprocess
import sys
import socket
import webview

def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def start_backend():
    if not is_port_open(8501):
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "app.py",
            "--server.headless=true",
            "--server.port=8501",
            "--global.developmentMode=false"
        ])

if __name__ == '__main__':
    # 1. Start backend server in background if not already running
    server_thread = threading.Thread(target=start_backend, daemon=True)
    server_thread.start()
    
    # 2. Wait 2 seconds for server to be ready
    time.sleep(2)

    # 3. Open Standalone Window
    webview.create_window(
        title="NeuraQuery AI — Autonomous On-Device Data Intelligence",
        url="http://localhost:8501",
        width=1350,
        height=880,
        resizable=True
    )
    webview.start()