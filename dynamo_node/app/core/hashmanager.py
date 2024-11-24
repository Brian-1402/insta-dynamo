import asyncio
from collections import defaultdict
from typing import Dict, List, Tuple
from app.core.hashring import HashRing
from app.core.config import NODE_ID, VNODES, N_REPLICAS
import hashlib

class KeyValueStorage:
    """Handles key-value storage and retrieval."""
    def __init__(self):
        self.store: Dict[str, Tuple[str,str]] = {}

    def add(self, key: str, value: Tuple[str,str]):
        self.store[key] = value

    def get(self, key: str) -> Tuple[str,str]:
        return self.store.get(key)

    def remove(self, key: str):
        if key in self.store:
            del self.store[key]
    
    def clear(self):
        self.store.clear()

    def list_keys(self) -> List[str]:
        return list(self.store.keys())

class DistributedKeyValueManager:
    """
    Manages consistent hashing and key-value storage.

    - Maintains a hash ring to map keys to nodes.
    - Uses KeyValueStorage for managing local key-value storage.
    - Handles addition of nodes, key transfer logic, and pending key transfers.
    """

    def __init__(self, nodes: List[str], node_id: str, vnodes: int = VNODES, replicas: int = N_REPLICAS):
        self.node_id = node_id
        # self.nodes as the union of nodes and nodeid
        self.nodes = list(set(nodes + [node_id]))
        self.hash_ring = HashRing(nodes=self.nodes, hash_fn=self._custom_hash, vnodes=vnodes, replicas=replicas)
        self.kv_storage = KeyValueStorage()  # Uses the KeyValueStorage class
        self.pending_transfers: Dict[str, List[str]] = defaultdict(list)  # Pending key transfers to other nodes

    @staticmethod
    def _hash_key(key: str) -> int:
        """Hashes a key using SHA-256."""
        return int(hashlib.sha256(key.encode()).hexdigest(), 16)

    def _custom_hash(self, key: str) -> int:
        """Supports custom hash function for node and key differentiation."""
        if isinstance(key, str) and len(key) == 64 and all(c in '0123456789abcdef' for c in key.lower()):
            return int(key, 16)
        return self._hash_key(key)

    def add_key_value(self, key: str, value: str):
        """
        Adds a key-value pair to the local storage if the key belongs to this node.
        """
        responsible_nodes = self.hash_ring.get_all_nodes(key)
        if self.node_id in responsible_nodes:
            self.kv_storage.add(key, value)
            return (True,[])
        else: 
            return (False, responsible_nodes)

    def get_value(self, key: str) -> str:
        """Retrieves the value for a key from local storage."""
        return self.kv_storage.get(key)

    def remove_key(self, key: str):
        """Removes a key from local storage."""
        self.kv_storage.remove(key)

    def list_local_keys(self) -> List[str]:
        """Lists all keys stored locally."""
        return self.kv_storage.list_keys()

    def add_node(self, new_node: str) -> List[str]:
        """
        Adds a new node to the hash ring and determines keys to transfer.
        
        Returns:
            List[str]: Keys that need to be transferred to the new node.
        """
        # print(f"Adding node {new_node}...")
        # check if already existing
        if new_node in self.nodes:
            return []
        
        self.hash_ring.add_node(new_node)
        transfer_keys = []

        for key in self.list_local_keys():
            new_responsible_nodes = self.hash_ring.get_all_nodes(key)

            if new_node in new_responsible_nodes and self.node_id not in new_responsible_nodes:
                # This key now belongs to the new node, transfer it
                transfer_keys.append(key)
                self.pending_transfers.setdefault(new_node, []).append(key)
                # self.remove_key(key)

        # print(f"Node {self.node_id} transfers {len(transfer_keys)} keys to {new_node}.")
        return transfer_keys

    def reset(self):
        """Resets the key-value storage and hash ring."""
        self.kv_storage.clear()
        self.pending_transfers.clear()
        self.nodes = [self.node_id]
        self.hash_ring = HashRing(nodes=[self.node_id], hash_fn=self._custom_hash, vnodes=VNODES, replicas=N_REPLICAS)

    def export_ring(self) -> dict:
        return self.hash_ring.export_metadata()

    @classmethod
    def reconstruct(cls, ring_metadata: dict, node_id: str, vnodes: int = VNODES, replicas: int = N_REPLICAS) -> "DistributedKeyValueManager":
        """
        Reconstructs a DistributedKeyValueManager instance from the exported hash ring metadata.

        Args:
            ring_metadata (dict): Metadata exported from the hash ring.
            node_id (str): ID of the current node.
            vnodes (int): Default number of virtual nodes for the hash ring.
            replicas (int): Default number of replicas for the hash ring.

        Returns:
            DistributedKeyValueManager: A reconstructed DistributedKeyValueManager instance.
        """
        # Reconstruct the hash ring
        hash_ring = HashRing.reconstruct_ring(ring_metadata, vnodes=vnodes, replicas=replicas)

        # Create a new manager instance with the reconstructed hash ring
        manager = cls(nodes=list(ring_metadata["physical_nodes"].keys()), node_id=node_id)
        manager.hash_ring = hash_ring  # Replace the default hash ring with the reconstructed one

        # Use default empty values for storage and pending transfers
        manager.kv_storage = KeyValueStorage()
        manager.pending_transfers = {}

        return manager