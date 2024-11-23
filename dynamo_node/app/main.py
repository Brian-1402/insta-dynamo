from fastapi import FastAPI
from app.api import endpoints

# Initialize FastAPI app
app = FastAPI()

# Include API routes
app.include_router(endpoints.router)