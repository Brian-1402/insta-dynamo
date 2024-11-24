from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from pathlib import Path
import uvicorn
from routes.auth import auth_router
from routes.image import image_router

import dotenv
dotenv.load_dotenv()

# Initialize the app
app = FastAPI()

# Include the auth router
app.include_router(auth_router, prefix="/auth")
app.include_router(image_router, prefix="/image")

# Define paths relative to the backend/src directory
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"

# Mount static files
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR / "static")), name="static")

# Load templates
templates = Jinja2Templates(directory=str(FRONTEND_DIR / "templates"))

# @app.on_event("startup")
# async def debug_routes():
#     print("\nRegistered Routes:")
#     for route in app.routes:
#         print(f"Path: {route.path}")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home Page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    """Login Page"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/signup", response_class=HTMLResponse)
async def signup(request: Request):
    """Signup Page"""
    return templates.TemplateResponse("signup.html", {"request": request})

@app.get("/upload", response_class=HTMLResponse)
async def upload(request: Request):
    """Image Upload Page"""
    return templates.TemplateResponse("upload.html", {"request": request})

@app.get("/gallery", response_class=HTMLResponse)
async def gallery(request: Request):
    """Gallery Page"""
    return templates.TemplateResponse("view.html", {"request": request})


# Main entry point
if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )