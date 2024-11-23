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
from pydantic import BaseModel
from sortedcontainers import SortedDict
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, Response
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, File, UploadFile

# Configure logging
logging.basicConfig(level=logging.INFO, 
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

            async with connection.get("/", timeout=aiohttp.ClientTimeout(total=10)) as response:
                logger.info(f"Response received from node {node_id}: {response.status}")
                if response.status != 200:
                    logger.error(f"Node {node_id} did not respond correctly (status: {response.status}).")
                    return False

            logger.info(f"Node {node_id} passed connection test.")

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
        target_nodes = await self.get_target_nodes(key)

        if not target_nodes:
            logger.warning(f"No target nodes found for key {key}")
            return False
        
        async def _write_to_node(node):
            try:
                async with self.connection_pool[node['physical_node']].post(
                    '/put_image',
                    data={'username': username, 'key': key},
                    files={'image': image_file.file}
                ) as response:
                    return response.status == 200
            except Exception as e:
                logger.error(f"Write failed to {node}: {e}")
                return False

        # Write to any one of the target nodes
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
        target_nodes = await self.get_target_nodes(key)
        if not target_nodes:
            logger.warning(f"No target nodes found for key {key}")
            return None
        
        async def _read_from_node(node):
            try:
                async with self.connection_pool[node['physical_node']].get(
                    '/get_image', 
                    params={'username': username, 'key': key}
                ) as response:
                    if response.status == 200:
                        # response object would be FileResponse
                        # Get the raw content and headers
                        content = await response.read()
                        headers = dict(response.headers)
                        
                        # Pass through the response directly
                        return Response(
                            content=content,
                            headers=headers,
                            status_code=response.status
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

# @app.get("/ring_state")
# async def get_ring_state():
#     """Endpoint to get the current ring state"""
#     return {
#         "virtual_nodes": list(control_panel.virtual_nodes.keys()),
#         "physical_nodes": list(control_panel.connection_pool.keys()),
#         "node_details": {
#             node_id: {
#                 "host": node_info["host"],
#                 "port": node_info["port"]
#             } for node_id, node_info in control_panel.virtual_nodes.items()
#         }
#     }

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

# # CLI for adding nodes
# def cli_add_node():
#     """
#     Command-line interface for adding a node to the Dynamo ring.
#     """
#     parser = argparse.ArgumentParser(description='Add a node to the Dynamo ring')
#     parser.add_argument('--node-id', required=True, help='Unique identifier for the node')
#     parser.add_argument('--host', required=True, help='Host address of the node')
#     parser.add_argument('--port', type=int, required=True, help='Port number of the node')
    
#     # If no arguments provided, enter interactive mode
#     if len(sys.argv) == 1:
#         print("Interactive Node Addition")
#         node_id = input("Enter Node ID: ")
#         host = input("Enter Host (e.g., localhost): ")
#         port = int(input("Enter Port: "))
#     else:
#         args = parser.parse_args()
#         node_id = args.node_id
#         host = args.host
#         port = args.port

#     # Attempt to add node
#     import requests
#     try:
#         response = requests.post('http://localhost:8000/add_node', json={
#             'node_id': node_id,
#             'host': host,
#             'port': port
#         })
#         result = response.json()
        
#         if result.get('success'):
#             print(f"Node {node_id} added successfully!")
#         else:
#             print(f"Failed to add node {node_id}")
#     except Exception as e:
#         print(f"Error adding node: {e}")

@app.get("/", response_class=HTMLResponse)
async def get_admin_dashboard(request: Request):
    """Render the admin dashboard template"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "websocket_url": "ws://localhost:8000/admin_dashboard"
    })

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