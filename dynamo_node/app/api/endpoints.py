import os
import aiofiles
from pydantic import BaseModel
from fastapi import APIRouter, Form, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from app.core.key_value import kv_storage
from app.core.file_ops import save_file, get_valid_file_path
from app.core.logger import logger
from app.core.connection import connector
router = APIRouter()

@router.get("/", response_class=RedirectResponse)
async def redirect_to_docs():
    return RedirectResponse(url="/docs")

@router.post("/upload")
async def upload_image_with_hash(
    username: str = Form(...), 
    key: str = Form(...),
    file: UploadFile = File(...),
):
    """
    Endpoint to upload an image and store its hash-to-filename mapping.
    """ 

    file_path = await save_file(file)
    kv_storage.add(key, file_path)

    return {
        "message": "File uploaded successfully",
        "filename": file.filename,
        "key": key,
        "username": username
    }

@router.get("/fetch/{key}")
async def fetch_image_by_hash(
    key: str,
    # key: str = Path(..., regex="^[a-fA-F0-9]{64}$")  # Ensures 64 hex characters
):
    """
    Endpoint to fetch an image using its hash.
    """
    try:
        file_path = get_valid_file_path(key)
    except HTTPException as e:
        raise e

    # Return the file directly as a response
    return FileResponse(file_path, media_type="image/jpeg", filename=os.path.basename(file_path))



# Define the Pydantic model for validation
class RingStateUpdate(BaseModel):
    node_id: int
    ip: str
    port: int

# Endpoint to receive updates for the ring state
@router.post("/update_ring")
async def update_ring(update: RingStateUpdate):
    """
    Endpoint to update the ring state.
    Receives a JSON object containing the node's ID, IP address, and port.
    
    Args:
        update (RingStateUpdate): Pydantic-validated input for the node's details.
    
    Returns:
        dict: Status of the update process.
    """
    try:
        # Simulate updating the internal ring state
        logger.info(f"Received ring state update: {update}")
        # Update logic goes here (e.g., modify shared state, notify other nodes, etc.)
        # For now, just add the node to the connection pool
        await connector.add_node(str(update.node_id), update.ip, update.port)
        # Need to send my hash ring data to the new node.
        # Send the pickle dump of the hash ring to the new node.
        # The new node will unpickle the data and update its own hash ring.
        conn = connector.get_connection(str(update.node_id))
        if conn is None:
            raise HTTPException(status_code=500, detail="Failed to connect to the new node.")
            
        
        return {"status": "success", "message": "Ring state updated successfully."}
    except Exception as e:
        logger.error(f"Error updating ring state: {e}")
        raise HTTPException(status_code=500, detail="Failed to update ring state.")