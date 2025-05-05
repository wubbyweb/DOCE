"""
DOCE (Division of Contract Efficiency) API
This FastAPI application provides an AI-powered invoice validation system
using Microsoft Semantic Kernel for contract and invoice processing.
"""

import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from doce.api import api_router
from doce.config import settings
from doce.database import engine, Base

# Initialize database and create tables
# This ensures all database models are created when the application starts
Base.metadata.create_all(bind=engine)

# Create necessary storage directories for file uploads
# These directories will store contract and invoice documents
os.makedirs(settings.file_storage.contract_path, exist_ok=True)
os.makedirs(settings.file_storage.invoice_path, exist_ok=True)

# Initialize FastAPI application
# This creates the main application instance with basic configuration
app = FastAPI(
    title=settings.app_name,
    description="AI Invoice Validation System using Microsoft Semantic Kernel",
    version="0.1.0",
)

# Configure Cross-Origin Resource Sharing (CORS)
# This allows the API to be accessed from different domains
# Note: In production, replace "*" with specific allowed origins for security
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
# All API endpoints will be prefixed with "/api"
app.include_router(api_router, prefix="/api")

# Mount static files for frontend (currently commented out)
# Will be implemented in future versions
# app.mount("/", StaticFiles(directory="doce/frontend/build", html=True), name="frontend")

@app.get("/")
async def read_root():
    """
    Root endpoint that returns basic API information
    Returns:
        dict: API welcome message and documentation URLs
    """
    return {
        "message": "Welcome to the Division of Contract Efficiency (DOCE) API",
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    }

# Application entry point
if __name__ == "__main__":
    """
    Run the application using uvicorn server
    Development mode with auto-reload enabled
    """
    import uvicorn
    uvicorn.run("doce.main:app", host="0.0.0.0", port=8000, reload=True)