"""
FastAPI Application for Uploading and Fetching Images by Hash.
"""

from collections import defaultdict
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from hashlib import sha256
from typing import Dict, Set, List
from uhashring import HashRing
import os
import aiofiles

# Initialize FastAPI app
app = FastAPI()

# Global node ID
NODE_ID = "node1"

# In-memory hash table
hash_table: Dict[str, str] = {}

class KeyValueStorage:
    """Handles key-value storage and retrieval."""
    def __init__(self):
        self.store: Dict[str, str] = {}

    def add(self, key: str, value: str):
        self.store[key] = value

    def get(self, key: str) -> str:
        return self.store.get(key)

    def remove(self, key: str):
        if key in self.store:
            del self.store[key]

    def list_keys(self) -> List[str]:
        return list(self.store.keys())


class ConsistentHashManager:
    """Manages consistent hashing and node operations."""
    def __init__(self, nodes: List[str], node_id: str):
        self.node_id = node_id
        self.hash_ring = HashRing(nodes=nodes)
        self.pending_transfers: Dict[str, Set[str]] = {}  # Track pending transfers for new nodes
        self.node_key_map = defaultdict(set)  # Tracks keys assigned to each node

    def add_node(self, new_node: str) -> Set[str]:
        """
        Adds a new node to the hash ring and determines the keys to transfer to the new node.
        """
        print(f"Adding node {new_node}...")
        
        old_hash_ring = HashRing(nodes=self.hash_ring.nodes)
        self.hash_ring.add_node(new_node)
        print(f"Hash ring updated. Current nodes: {self.hash_ring.nodes}")
        
        transfer_keys = set()
        for key in self.node_key_map[self.node_id]:
            old_responsible_node = old_hash_ring.get_node(key)
            new_responsible_node = self.hash_ring.get_node(key)
            
            # Debugging key transfer decision
            # print(f"Key {key} was handled by {old_responsible_node}, now handled by {new_responsible_node}")
            
            if old_responsible_node == self.node_id and new_responsible_node == new_node:
                transfer_keys.add(key)

        # Update node key maps
        self.pending_transfers[new_node] = transfer_keys
        self.node_key_map[new_node].update(transfer_keys)
        self.node_key_map[self.node_id].difference_update(transfer_keys)

        print(f"Node {self.node_id} transfers {len(transfer_keys)} keys to {new_node}")
        return transfer_keys

    def remove_node(self, node: str):
        if node not in self.hash_ring.nodes:
            raise ValueError(f"Node {node} not in hash ring.")
        self.hash_ring.remove_node(node)
        if node in self.pending_transfers:
            del self.pending_transfers[node]
        if node in self.node_key_map:
            del self.node_key_map[node]

    def assign_key(self, key: str):
        responsible_node = self.hash_ring.get_node(key)
        self.node_key_map[responsible_node].add(key)

    def print_node_key_distribution(self):
        print("Node-to-Key Distribution:")
        for node, keys in self.node_key_map.items():
            print(f"  {node}: {len(keys)} keys")

    def get_pending_transfers(self, node: str) -> Set[str]:
        return self.pending_transfers.get(node, set())


kv_storage = KeyValueStorage()
hash_manager = ConsistentHashManager(nodes=["node1", "node2", "node3"], node_id=NODE_ID)

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
    file_contents = await file.read()
    file_path = os.path.join(STORE_DIR, file.filename)

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(file_contents)
    
    # Update the hash table
    kv_storage.add(key, file_path)

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
    file_path = kv_storage.get(key)
    if not file_path:
        raise HTTPException(status_code=404, detail="Hash not found")
    
    # Possible to have key but not the file? some kind of deletion inconsistency is possible after all.
    if not os.path.exists(file_path):  # Use synchronous check since aiofiles lacks an `exists` function
        raise HTTPException(status_code=404, detail="Hash found but file not found")
    
    async with aiofiles.open(file_path, "rb") as f:
        file_content = await f.read()
    
    # Return the file as a response
    # ! change this, coz idk the file name. plus, there's pagination of directories and all, so path is more meaningful than just the name
    return FileResponse(file_path, media_type="image/jpeg", filename=file_path)