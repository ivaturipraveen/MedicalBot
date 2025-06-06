# Medical Appointment Booking System

A full-stack application with a FastAPI backend and HTML/CSS/JavaScript frontend for managing medical appointments.

## Setup

1. **Install dependencies**:
   ```
   pip install -r requirements.txt
   ```

2. **Configure OpenAI API Key**:
   - Edit the `.env` file and add your OpenAI API key:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

## Running the Application

Run the following command to start both the backend and frontend servers:

```
python run.py
```

This will:
- Start the FastAPI backend on http://localhost:8000
- Start a simple HTTP server for the frontend on http://localhost:3000
- Open your browser to the frontend application

## Manual Setup (Alternative)

If you prefer to run the servers separately:

1. **Run the backend**:
   ```
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **Serve the frontend**:
   - You can use any HTTP server, for example with Python:
   ```
   python -m http.server 3000
   ```
   
3. Open your browser to http://localhost:3000

## Application Structure

- `main.py` - FastAPI backend application
- `index.html`, `script.js`, `styles.css` - Frontend application
- `requirements.txt` - Python dependencies
- `.env` - Environment variables (contains OpenAI API key)
- `run.py` - Script to run both backend and frontend 