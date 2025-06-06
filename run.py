import os
import subprocess
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
import time

def run_backend():
    """Run the FastAPI backend server"""
    print("Starting FastAPI backend server...")
    subprocess.Popen(["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"])
    print("Backend server running at http://localhost:8000")

def run_frontend():
    """Run a simple HTTP server for the frontend"""
    print("Starting frontend server...")
    server = HTTPServer(('localhost', 3000), SimpleHTTPRequestHandler)
    print("Frontend server running at http://localhost:3000")
    server.serve_forever()

def open_browser():
    """Open browser to the frontend application"""
    print("Opening application in browser...")
    time.sleep(2)  # Wait for servers to start
    webbrowser.open('http://localhost:3000')

if __name__ == "__main__":
    # Check if .env file exists, if not create it with placeholder
    if not os.path.exists(".env"):
        with open(".env", "w") as f:
            f.write("OPENAI_API_KEY=your_openai_api_key_here\n")
        print("Created .env file. Please edit it to add your OpenAI API key.")
    
    # Start backend in a separate thread
    backend_thread = threading.Thread(target=run_backend)
    backend_thread.daemon = True
    backend_thread.start()
    
    # Open browser in a separate thread
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Run frontend in the main thread
    run_frontend() 