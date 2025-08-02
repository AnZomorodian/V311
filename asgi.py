"""
ASGI entry point for the F1 Analytics Dashboard
This module provides ASGI-compatible application entry point for deployment with gunicorn
"""

from main import app

# Export the FastAPI app as an ASGI application
# This allows gunicorn to run with an ASGI worker
application = app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)