import asyncio
import aiohttp
from app.core.logger import logger

class NodeConnector:
    def __init__(self, node_id, ring_nodes):
        self.connection_pool = {}
        self.node_id = node_id
        # Check if there's an existing event loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:  # No event loop in the current thread
            loop = None

        if loop:
            loop.create_task(self._initialize_nodes(ring_nodes))
        else:
            asyncio.run(self._initialize_nodes(ring_nodes))

    async def _initialize_nodes(self, ring_nodes):
        """
        Asynchronously initializes nodes by calling add_node concurrently.
        """
        # await asyncio.gather(
        #     *(self.add_node(node_id, ip, port) for node_id, (ip, port) in ring_nodes.items())
        # )    
        tasks = []
        for node_id, (ip, port) in ring_nodes.items():
            task = self.add_node(node_id, ip, port)
            tasks.append(task)

        await asyncio.gather(*tasks)

    async def add_node(self, node_id: str, host: str, port: int):
        connection = None
        try:
            if node_id == self.node_id:
                logger.info(f"Skipping connection to self ({node_id}).")
                return True
            # Attempt to create and test the connection
            connection = await self._create_node_connection(host, port)
            logger.info(f"Connection created for {node_id}. Testing...")

            async with connection.get("/", timeout=aiohttp.ClientTimeout(total=10)) as response:
                logger.info(f"Response received from node {node_id}: {response.status}")
                if response.status != 200:
                    logger.error(f"Node {node_id} did not respond correctly (status: {response.status}).")
                    return False

            logger.info(f"Node {node_id} passed connection test.")

            # Add the new node to the connection pool
            self.connection_pool[node_id] = connection

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

    def get_connection(self, node_id: str):
        return self.connection_pool.get(node_id, None)