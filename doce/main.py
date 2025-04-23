import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from doce.api import api_router
from doce.config import settings
from doce.database import engine, Base

# Create database tables
Base.metadata.create_all(bind=engine)

# Create upload directories if they don't exist
os.makedirs(settings.file_storage.contract_path, exist_ok=True)
os.makedirs(settings.file_storage.invoice_path, exist_ok=True)

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="AI Invoice Validation System using Microsoft Semantic Kernel",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api")

# Mount static files for frontend (will be implemented later)
# app.mount("/", StaticFiles(directory="doce/frontend/build", html=True), name="frontend")

@app.get("/")
def read_root():
    return {
        "message": "Welcome to the Division of Contract Efficiency (DOCE) API",
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("doce.main:app", host="0.0.0.0", port=8000, reload=True)