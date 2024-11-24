import random
import asyncio
import hashlib
import logging
import argparse
from typing import Dict, Any, Optional, List, Tuple

import aiohttp
from aiohttp import FormData
from fastapi.responses import Response
from fastapi import UploadFile

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


            logger.info(f"Node {node_id} passed connection test.")

            # Add the first node directly
            if len(self.connection_pool) == 0:
                url = f"http://{host}:{port}/join_ring"
                headers = {"Content-Type": "application/json"}
                payload = {
                    "node_data": {
                        "nodes": {
                            node_id: {"ip": host, "port": port}
                        }
                    },
                    "ring_metadata": {
                        "physical_nodes": {}
                    }
                }

                async with aiohttp.ClientSession() as session:
                    try:
                        async with session.post(url, headers=headers, json=payload) as response:
                            if response.status == 200:
                                logger.info(f"Successfully joined the ring: {await response.json()}")
                            else:
                                logger.error(f"Failed to join the ring. Status: {response.status}, Response: {await response.text()}")
                    except Exception as e:
                        logger.error(f"Error occurred while trying to join the ring: {e}")
                    self.connection_pool[node_id] = connection
                logger.info(f"First node {node_id} added successfully.")
                return True

            # Notify an existing node about the new node
            random_node_url = random.choice(list(self.connection_pool.values()))
            logger.info(f"Notifying existing node: {random_node_url}")

            # ring_state = await self._get_ring_from_node(random_node_url)
            # logger.info(f"Ring state fetched: {ring_state}")
            
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

            # if 'error' in ring_state:
            #     logger.error(f"Failed to get ring state: {ring_state['error']}")
            #     return False

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
                    async with session.post(f"{node_url}/invite_node", json=ring_state) as response:
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
                print(f"Uploading image with key: {key}")
                print(f"Form type: {type(form)}")
                print(f"Form fields: {form._fields}")
                print(f"form._fields[0]: {form._fields[0]}")
                print(f"form._fields[1]: {form._fields[1]}")
                print(f"form._fields[2]: {form._fields[2]}")
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