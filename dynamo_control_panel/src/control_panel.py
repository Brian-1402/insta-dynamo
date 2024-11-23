import os
import sys
import random
import asyncio
import hashlib
import logging
import argparse
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

import uvicorn
import aiohttp
from aiohttp import FormData
from pydantic import BaseModel
from sortedcontainers import SortedDict
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, Response, StreamingResponse
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, File, UploadFile, Depends, Form

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.basicConfig(level=logging.ERROR,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DynamoControlPanel:
    def __init__(self):
        #! Consistent Hashing Ring
        #! Don't maintain hash ring, we shall request for a hash ring from a random node in the ring
        # self.hash_ring = None
        self.virtual_nodes = {} #! TBD if needed
        # self.physical_nodes = {}
        
        #! (Not needed, no quorum checks by control panel) Replication and Consistency Parameters
        # self.N = 3  # Total number of replicas
        # self.R = 2  # Read replicas
        # self.W = 2  # Write replicas

        # Async connection pool for all nodes (control panel just knows where the nodes are, and nothing about the ring structure)
        self.connection_pool = {}
        
        # # Nodes to notify when ring state changes
        # self.notification_nodes = []

        # virtual nodes per physical node
        # self.num_virt_nodes = 3

    @staticmethod
    def hash_key(key: str) -> int:
        """Generate a consistent hash for a given key."""
        return int(hashlib.sha256(key.encode()).hexdigest(), 16)

    async def add_node(self, node_id: str, host: str, port: int):
        connection = None
        try:
            logger.info("Starting node addition...")

            # Attempt to create and test the connection
            connection = await self._create_node_connection(host, port)
            logger.info(f"Connection created for {node_id}. Testing...")

            #! REPLACE WHEN THE BELOW ENDPOINT IS CREATED IN DYNAMO NODE
            # async with connection.get("/", timeout=aiohttp.ClientTimeout(total=10)) as response:
            #     logger.info(f"Response received from node {node_id}: {response.status}")
            #     if response.status != 200:
            #         logger.error(f"Node {node_id} did not respond correctly (status: {response.status}).")
            #         return False

            # logger.info(f"Node {node_id} passed connection test.")

            # Add the first node directly
            if len(self.connection_pool) == 0:
                self.connection_pool[node_id] = connection
                logger.info(f"First node {node_id} added successfully.")
                return True

            # Notify an existing node about the new node
            random_node_url = random.choice(list(self.connection_pool.values()))
            logger.info(f"Notifying existing node: {random_node_url}")

            ring_state = await self._get_ring_from_node(random_node_url)
            logger.info(f"Ring state fetched: {ring_state}")
            
            # Create virtual nodes
            #! TODO: Most likely wont need to maintain mappings except the connections
            # for i in range(self.num_virt_nodes):  # 3 virtual nodes per physical node
            #     virtual_node_id = f"{node_id}-v{i}"
            #     virtual_hash = self.hash_key(virtual_node_id)
                
            #     # Update the ring state to include the new virtual node
            #     ring_state[virtual_hash] = virtual_node_id
            #     self.virtual_nodes[virtual_node_id] = {
            #         "physical_node": node_id,
            #         "host": host,
            #         "port": port
            #     }

            if 'error' in ring_state:
                logger.error(f"Failed to get ring state: {ring_state['error']}")
                return False

            # Add the new node to the connection pool
            self.connection_pool[node_id] = connection
            add_response = await self._notify_nodes_about_addition(random_node_url, node_id, host, port)
            if not add_response:
                logger.warning(f"Failed to notify existing nodes about new node {node_id}.")
                return False

            logger.info(f"Node {node_id} added successfully.")
            return True

        except asyncio.TimeoutError:
            logger.error(f"Timeout while connecting to node {node_id} at {host}:{port}.")
            return False

        except aiohttp.ClientError as e:
            logger.error(f"Failed to connect to node {node_id} at {host}:{port}: {e}")
            return False

        except Exception as e:
            import traceback
            logger.error(f"Unexpected error while adding node {node_id}: {e}\n{traceback.format_exc()}")
            return False
        
        finally:
            if connection and node_id not in self.connection_pool:
                logger.info(f"Closing connection for {node_id}.")
                await connection.close()

    async def _create_node_connection(self, host: str, port: int):
        """
        Create an aiohttp ClientSession for a node.
        Ensure the session is properly managed.
        """
        return aiohttp.ClientSession(
            base_url=f"http://{host}:{port}",
            timeout=aiohttp.ClientTimeout(total=10)
        )


    async def _notify_nodes_about_addition(self, node_url: str, new_node_id: str, new_node_ip: str, new_node_port: int):
        """
        Notify one node (node_url) registered nodes about the new addition.
        """
        ring_state = {
            "node_id": new_node_id,
            "ip": new_node_ip,
            "port": new_node_port,
        }

        async def _send_update_to_node(node_url):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(f"{node_url}/update_ring", json=ring_state) as response:
                        return response.status == 200
            except Exception as e:
                logger.error(f"Failed to notify node {node_url}: {e}")
                return False

        update_response = await _send_update_to_node(node_url)
        if not update_response:
            logger.warning(f"Failed to notify node {node_url} about new node")
            return False
        return True
        # # Notify all registered nodes concurrently
        # notification_tasks = [
        #     _send_update_to_node(f"http://{node['host']}:{node['port']}")
        #     for node in self.virtual_nodes.values()
        # ]
        
        # await asyncio.gather(*notification_tasks)

    async def _get_ring_from_node(self, node_url: str) -> Dict:
        """
        Get the current hash ring from a random node.
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{node_url}/get_ring") as response:
                    if response.status == 200:
                        return await response.json()
                    return {"error": "Failed to get ring from node"}
        except Exception as e:
            logger.error(f"Failed to get ring from node {node_url}: {e}")
            return {"error": str(e)}
    
    async def _get_target_nodes(self, key: str) -> List[Dict]:
        """
        Find target nodes for a given key using consistent hashing.
        Returns a list of N nodes responsible for the key.
        """
        target_nodes = []
        if len(self.connection_pool) == 0:
            logger.warning("No nodes in the ring")
            return target_nodes
        
        # Directly use the get_target_nodes endpoint of the Dynamo Nodes
        node_url = random.choice(list(self.connection_pool.values()))
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{node_url}/get_target_nodes", params={'key': key}) as response:
                    if response.status == 200:
                        target_nodes = await response.json()
                    else:
                        logger.warning(f"Failed to get target nodes for key {key}")
        except Exception as e:
            logger.error(f"Failed to get target nodes for key {key}: {e}")
        
        return target_nodes
    
      # # Find random node to get the ring from
        # random_node = random.choice(list(self.connection_pool.values()))
        # ring_state = await self._get_ring_from_node(random_node)
        # if 'error' in ring_state:
        #     logger.error(f"Failed to get ring state: {ring_state['error']}")
        #     return target_nodes
        
        # # Find nodes in the ring
        # sorted_hashes = SortedDict(ring_state)
        # start_index = next(i for i, h in enumerate(sorted_hashes) if h >= key_hash)
        
        # for i in range(self.N):
        #     node_hash = sorted_hashes[(start_index + i) % len(sorted_hashes)]
        #     virtual_node = ring_state[node_hash]
        #     node_info = self.virtual_nodes[virtual_node]
        #     target_nodes.append(node_info)
        
        # return target_nodes

    async def put_image(self, username: str, key: str, image_file: UploadFile):
        """
        PUT operation to store an image in the distributed storage (Write quorum handled by nodes)
        """
        #! REPLACE BELOW BY target_nodes = await self._get_target_nodes(key)
        target_nodes = list(self.connection_pool.keys())
        if not target_nodes:
            logger.warning(f"No target nodes found for key {key}")
            return False

        async def _write_to_node(node):
            try:
                # file_content = await image_file.read()
                form = FormData()
                form.add_field("username", username)
                form.add_field("key", key)
                form.add_field(
                    "file", 
                    filename=image_file.filename, 
                    value=image_file.file,
                    content_type=image_file.content_type,
                )
                # image_file.file.seek(0)  # Reset the file pointer again
                #! REPLACE NODE BY node['physical_node'] depending on what get_target_nodes returns
                async with self.connection_pool[node].post(
                    "/upload", 
                    data=form
                ) as response:
                    return response.status == 200
            except Exception as e:
                logger.error(f"Write failed to {node}: {e}")
                return False

        write_response = await _write_to_node(random.choice(target_nodes))
        if not write_response:
            logger.warning(f"Failed to write image for key {key}")
            return False

        return True
        # # Concurrent writes
        # write_results = await asyncio.gather(
        #     *[_write_to_node(node) for node in target_nodes[:self.W]]
        # )
        
        # write_successes = sum(write_results)
        
        # if write_successes < self.W:
        #     logger.warning(f"Write quorum not met. Successful writes: {write_successes}")
        #     return False
        
        # return True

    async def get_image(self,username: str, key: str):
        """
        GET operation to retrieve an image from the distributed storage (Read quorum handled by nodes)
        """
        #! REPLACE below as target_nodes = await self._get_target_nodes(key)
        target_nodes = list(self.connection_pool.keys())
        if not target_nodes:
            logger.warning(f"No target nodes found for key {key}")
            return None
        
        async def _read_from_node(node):
            try:
                #! REPLACE NODE BY node['physical_node'] depending on what get_target_nodes returns
                async with self.connection_pool[node].get(
                    f'/fetch/{key}', 
                ) as response:
                    if response.status == 200:
                        # response object would be FileResponse
                        # Get the raw content and headers
                        content = await response.read()
                        content_type = response.content_type  # Preserve the Content-Type

                        # Return the file as a Response
                        return Response(
                            content=content,
                            media_type=content_type,
                            headers={"Content-Disposition": f"inline; filename={key}"}
                        )
                    return None
            except Exception as e:
                logger.error(f"Read failed from {node}: {e}")
                return None
        
        # Read from any one of the target nodes
        read_response = await _read_from_node(random.choice(target_nodes))
        if read_response:
            return read_response
        else:
            logger.warning(f"Could not read image for key {key}")
            return None

        # # Concurrent reads
        # read_results = await asyncio.gather(
        #     *[_read_from_node(node) for node in target_nodes[:self.R]]
        # )
        
        # valid_results = [r for r in read_results if r is not None]
        
        # if not valid_results:
        #     logger.warning(f"Could not read image for key {key}")
        #     return None
        
        # #! Basic version reconciliation based on timestamp (Last Write Wins)
        # valid_results.sort(key=lambda x: x['timestamp'], reverse=True)
        # return valid_results[0]

# Dynamically resolve the directory of this file
BASE_DIR = Path(__file__).resolve().parent.parent

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
        "control_panel:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True
    )