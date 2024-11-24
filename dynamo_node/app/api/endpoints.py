import asyncio
import os
from typing import Dict
import aiofiles
import httpx
from pydantic import BaseModel
from fastapi import APIRouter, Body, Form, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from app.core.state import ns
from app.core.file_ops import save_file, get_valid_file_path
from app.core.logger import logger
from httpx import AsyncClient


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
    ns.manager.add_key_value(key, (username, file_path))
    
    # log the current total keys
    logger.info(f"Total keys: {len(ns.manager.kv_storage.store)}")

    return {
        "message": "File uploaded successfully",
        "filename": file.filename,
        "key": key,
        "username": username,
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
    return FileResponse(
        file_path, media_type="image/jpeg", filename=os.path.basename(file_path)
    )



@router.post("/invite_node")
async def invite_node(payload: dict = Body(...)):
    """
    Sent by control panel to an existing node, signaling it to add the new node to its ring.
    Sends the ring data to the new node.
    """
    node_id = payload["node_id"]
    ip = payload["ip"]
    port = payload["port"]
    try:
        # Prepare node_dict in the format of NodeMapping
        ring_nodes = ns.ring_nodes
        node_mapping_json = {
            "nodes": {
                node_id: {"ip": ip, "port": port} for node_id, (ip, port) in ns.ring_nodes.items()
            }
        }# Add the new node to the node mapping

        node_mapping_json["nodes"][node_id] = {"ip": ip, "port": port}
        
        ring_metadata_json = {"physical_nodes": ns.manager.export_ring()["physical_nodes"]}
        target_url = f"http://{ip}:{port}/join_ring"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                target_url,
                json={ "node_data": node_mapping_json, "ring_metadata": ring_metadata_json},
            )
        
        if response.status_code != 200:
            raise HTTPException( status_code=500, detail=f"Failed to send ring data to the new node. Response: {response.text}")
        return {"message": "Ring data successfully sent to the new node."}
    
    except httpx.RequestError as exc:
        raise HTTPException( status_code=500, detail=f"An error occurred while sending data to the node: {exc}")


@router.post("/ring_transfer")
async def ring_transfer(payload: dict = Body(...)):
    """
    Sent by a new node instance, signalling everyone to add it to their ring.
    Also triggers the transfer of keys to the new node.
    """
    node_id = payload["node_id"]
    ip = payload["ip"]
    port = payload["port"]
    try:
        await ns.connector.add_node(node_id, ip, port)

        # Get keys to transfer
        transfer_keys = ns.manager.add_node(node_id)
        logger.info(f"Transferring keys to node {node_id}: {len(transfer_keys)} keys")

        async with AsyncClient() as client:
            for key in transfer_keys:
                username, file_path = ns.manager.get_value(key)
                if not file_path:
                    continue  # Skip if file not found
                async with aiofiles.open(file_path, "rb") as file:
                    file_data = await file.read()
                    response = await client.post(
                        f"http://{ip}:{port}/upload",
                        data={"key": key, "username": username},
                        files={
                            "file": ( os.path.basename(file_path), file_data, "image/jpeg",)
                        },
                    )
                    if response.status_code != 200:
                        logger.error( f"Failed to transfer key {key} to node {node_id}")
                    else:  # Remove the file if transfer was successful
                        os.remove(file_path)
                        ns.manager.remove_key(key)

        return {
            "status": "success",
            "message": "Ring state updated and files transferred successfully.",
        }

    except Exception as e:
        logger.error(f"Error updating ring state: {e}")
        raise HTTPException(status_code=500, detail="Failed to update ring state.")


# Define the structure for the IP-Port pair
class IPPort(BaseModel):
    ip: str
    port: int


class NodeMapping(BaseModel):
    nodes: Dict[str, IPPort]


class RingMetadata(BaseModel):
    physical_nodes: Dict[str, int]


@router.post("/join_ring")
async def join_ring(node_data: NodeMapping, ring_metadata: RingMetadata):
    """
    Endpoint to join an existing ring.
    Receives the metadata of the existing ring and updates the local ring state.
    """
    # Simulate updating the internal ring state
    logger.info(f"Received ring metadata: {ring_metadata.dict()}")
    # Update logic goes here (e.g., modify shared state, notify other nodes, etc.)
    # For now, just update the hash ring
    ns.manager.reconstruct(ring_metadata.dict(), ns.node_id)
    node_dict = {
        node_id: (node.ip, node.port) for node_id, node in node_data.nodes.items()
    }
    ns.initialize_connections(node_dict)
    logger.info(f"Updated ring state with new node data: {ns.ring_nodes}")

    # call ring transfer for all nodes except myself. asyncrhonousely
    my_ip, my_port = ns.ring_nodes[ns.node_id]
        
    tasks = []
    my_node_id = ns.node_id
    my_ip, my_port = ns.ring_nodes[my_node_id]

    async with httpx.AsyncClient() as client:
        for node_id, (ip, port) in ns.ring_nodes.items():
            if node_id == my_node_id:
                continue  # Skip sending to self

            url = f"http://{ip}:{port}/ring_transfer"
            payload = { "node_id": my_node_id, "ip": my_ip, "port": my_port, }

            tasks.append(client.post(url, json=payload))

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        for node_id, response in zip(ns.ring_nodes.keys(), responses):
            if node_id == my_node_id:
                continue  # Already skipped self
            if isinstance(response, Exception):
                logger.info(f"Error contacting node {node_id}: {response}")
            else:
                logger.info(f"Response from node {node_id}: {response.status_code}")
                # also log the message
                logger.info(f"Response message from node {node_id}: {response.text}")

        return {"status": "success", "message": "Joined the ring successfully."}
