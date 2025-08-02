from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
import logging
import os
from f1_data_extractor import F1DataExtractor
from api_endpoints import router as api_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="F1 Analytics Dashboard",
    description="Professional Formula 1 data analysis platform",
    version="2.0.0"
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Initialize F1 data extractor
f1_extractor = F1DataExtractor()

# Include API routes
app.include_router(api_router, prefix="/api")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main dashboard page"""
    try:
        # Get available seasons for the dropdown
        seasons = f1_extractor.get_available_seasons()
        current_season = max(seasons) if seasons else 2024
        
        return templates.TemplateResponse("index.html", {
            "request": request,
            "seasons": seasons,
            "current_season": current_season
        })
    except Exception as e:
        logger.error(f"Error serving home page: {e}")
        return templates.TemplateResponse("index.html", {
            "request": request,
            "error": "Failed to load dashboard data",
            "seasons": [],
            "current_season": 2024
        })

@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    """Serve the about page"""
    return templates.TemplateResponse("about.html", {"request": request})

@app.get("/analysis", response_class=HTMLResponse)
async def analysis(request: Request):
    """Serve the analysis page"""
    try:
        seasons = f1_extractor.get_available_seasons()
        return templates.TemplateResponse("analysis.html", {
            "request": request,
            "seasons": seasons
        })
    except Exception as e:
        logger.error(f"Error serving analysis page: {e}")
        return templates.TemplateResponse("analysis.html", {
            "request": request,
            "error": "Failed to load analysis data",
            "seasons": []
        })

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "F1 Analytics Dashboard"}

# WSGI compatibility for gunicorn deployment
try:
    from wsgi_adapter import ASGIToWSGIAdapter
    # Store the original FastAPI app
    fastapi_app = app
    # Replace the app object with WSGI adapter for gunicorn compatibility
    app = ASGIToWSGIAdapter(fastapi_app)
    # Also export as application for compatibility
    application = app
except ImportError:
    # Fallback to FastAPI app if WSGI adapter is not available
    fastapi_app = app
    application = app

if __name__ == "__main__":
    # Use port 5000 for frontend visibility as specified in requirements
    port = int(os.getenv("PORT", 5000))
    # When running directly, use the original FastAPI app with uvicorn
    uvicorn.run(fastapi_app if 'fastapi_app' in locals() else app, host="0.0.0.0", port=port, log_level="info")
