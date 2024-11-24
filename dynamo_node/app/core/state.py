from app.core.config import NODE_ID, VNODES, N_REPLICAS, STORE_DIR
from app.core.connection import NodeConnector
from app.core.hashmanager import DistributedKeyValueManager
from pydantic import BaseModel, IPvAnyAddress, conint
from typing import Dict, Tuple
from app.core.logger import logger

class NodeState:
    def __init__(self):
        self.node_id = NODE_ID
        self.vnodes = VNODES
        self.n_replicas = N_REPLICAS
        self.store_dir = STORE_DIR
        self.connector = None
        self.manager = DistributedKeyValueManager(nodes=[NODE_ID], node_id=NODE_ID, vnodes=VNODES, replicas=N_REPLICAS)
        self.ring_nodes = None
        
    def initialize_connections(self, ring_nodes):
        self.connector = NodeConnector(self.node_id, ring_nodes)
        self.ring_nodes = ring_nodes

ns = NodeState()
logger.info(f"Node state initialized with ID: {ns.node_id}")