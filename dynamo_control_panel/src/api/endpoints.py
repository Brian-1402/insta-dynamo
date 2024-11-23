import sys
import asyncio
import uvicorn
import logging
from pathlib import Path

from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, Response
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, UploadFile, File

from src.core.control_panel import DynamoControlPanel

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.basicConfig(level=logging.ERROR,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Dynamically resolve the directory of this file
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Define paths for templates and static files
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
CSS_DIR = STATIC_DIR / "css"
JS_DIR = STATIC_DIR / "js"

# Create directories if they don't exist
TEMPLATES_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)
CSS_DIR.mkdir(exist_ok=True)
JS_DIR.mkdir(exist_ok=True)

# Admin Web Interface
app = FastAPI()

# Mount templates and static directories
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class NodeConfig(BaseModel):
    node_id: str
    host: str
    port: int

control_panel = DynamoControlPanel()

@app.post("/add_node")
async def add_node(node_config: NodeConfig):
    """Admin endpoint to add a new node to the Dynamo ring."""
    success = await control_panel.add_node(
        node_config.node_id, 
        node_config.host, 
        node_config.port
    )
    if success:
        return {"status":"success", "message": f"Added node with ID {node_config.node_id}, Host {node_config.host}, Port {node_config.port}"}
    return {"status": "error", "message": "Failed to add node, check logs for details"}

@app.post("/put_image")
async def put_image(username: str, key: str, image: UploadFile = File(...)):
    """
    Backend endpoint for putting an image into the distributed storage.
    """
    success = await control_panel.put_image(username, key, image)
    return {"success": success}

@app.get("/get_image")
async def get_image(username:str, key: str):
    """
    Backend endpoint for retrieving an image from distributed storage.
    """
    image_data = await control_panel.get_image(username, key)
    if image_data:
        return image_data
    return {"success": False, "message": "Image not found"}

@app.websocket("/admin_dashboard")
async def admin_dashboard(websocket: WebSocket):
    """WebSocket endpoint for real-time admin dashboard updates."""
    await websocket.accept()
    try:
        while True:
            # Get current ring state
            ring_state = {
                "virtual_nodes": list(control_panel.virtual_nodes.keys()),
                "physical_nodes": list(control_panel.connection_pool.keys())
            }
            await websocket.send_json(ring_state)
            await asyncio.sleep(5)  # Update every 5 seconds
    except WebSocketDisconnect:
        logger.info("Admin dashboard WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")

@app.get("/", response_class=HTMLResponse)
async def get_admin_dashboard(request: Request):
    """Render the admin dashboard template"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "websocket_url": "ws://localhost:8000/admin_dashboard"
    })

#! Add this global dictionary to store hashes for admin testing [Temp only needed for admin testing]
admin_image_store = {}

@app.post("/admin/upload_image")
async def admin_upload_image(image: UploadFile = File(...)):
    """
    Admin endpoint to upload an image and store its hash for later retrieval.
    """
    try:
        # Read the file to calculate the hash
        file_content = await image.read()
        hashed_key = DynamoControlPanel.hash_key(file_content.decode("latin1"))
        image.file.seek(0)  # Reset the pointer so the file can be reused

        # Store the file using put_image (simulate admin username as 'admin')
        await control_panel.put_image("admin", str(hashed_key), image)

        # Store the hash and filename for admin retrieval
        admin_image_store[image.filename] = hashed_key
        return {"success": True, "message": "Image uploaded successfully", "key": hashed_key}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.get("/admin/list_images")
async def list_uploaded_images():
    """
    Endpoint to return the list of filenames of uploaded images.
    """
    try:
        return {"success": True, "images": list(admin_image_store.keys())}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.get("/admin/view_image/{filename}")
async def admin_view_image(filename: str):
    """
    Admin endpoint to view an uploaded image using its filename.
    """
    try:
        if filename not in admin_image_store:
            return {"success": False, "message": "Image not found"}

        # Retrieve the image using its hash
        hashed_key = admin_image_store[filename]
        response = await control_panel.get_image("admin", str(hashed_key))

        if response:
            return response # Return the image as a response
        return {"success": False, "message": "Image retrieval failed"}
    except Exception as e:
        return {"success": False, "message": str(e)}


# Main entry point with CLI support
if __name__ == "__main__":
    # if len(sys.argv) > 1 and sys.argv[1] == 'add_node':
    #     cli_add_node()
    # else:
    uvicorn.run(
        "src.api.endpoints:app",  # Update to the correct module path
        host="0.0.0.0",
        port=8000,
        reload=True
    )