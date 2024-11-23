"""
FastAPI Application for Uploading and Fetching Images by Hash.

This application provides two main endpoints:
1. **POST /upload**: Allows users to upload an image along with its hash and username. 
   The image is stored locally, and a hash-to-filename mapping is maintained in memory.
2. **GET /fetch/{hash}**: Fetches and returns an image based on its hash.
"""

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from hashlib import sha256
from typing import Dict
import os
import aiofiles

# Initialize FastAPI app
app = FastAPI()

# In-memory hash table
hash_table: Dict[str, str] = {}

# Ensure the storage directory exists
STORE_DIR = "./store"
os.makedirs(STORE_DIR, exist_ok=True)

# Pydantic model for upload request
class UploadRequest(BaseModel):
    username: str

@app.post("/upload")
async def upload_image_with_hash(
    username: str = Form(...), 
    key: str = Form(...),
    file: UploadFile = File(...), 
):
    """
    Endpoint to upload an image and store its hash-to-filename mapping.
    """
    # Read file contents
    file_contents = await file.read()
    
    # Compute file hash
    # key = sha256(file_contents).hexdigest()

    # Save the file to the store directory using aiofiles
    file_path = os.path.join(STORE_DIR, file.filename)
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(file_contents)
    
    # Update the hash table
    hash_table[key] = file.filename

    return {
        "message": "File uploaded successfully",
        "filename": file.filename,
        "key": key,
        "username": username
    }

@app.get("/fetch/{key}")
async def fetch_image_by_hash(key: str):
    """
    Endpoint to fetch an image using its hash.
    """
    # Lookup the hash in the hash table
    filename = hash_table.get(key)
    if not filename:
        raise HTTPException(status_code=404, detail="Hash not found")
    
    # Generate file path
    file_path = os.path.join(STORE_DIR, filename)
    
    # Check if the file exists using aiofiles
    if not os.path.exists(file_path):  # Use synchronous check since aiofiles lacks an `exists` function
        raise HTTPException(status_code=404, detail="Hash found but file not found")
    
    # Read file content asynchronously
    async with aiofiles.open(file_path, "rb") as f:
        file_content = await f.read()
    
    # Return the file as a response
    return FileResponse(file_path, media_type="image/jpeg", filename=filename)