from collections import defaultdict
from typing import Dict, Set, List
# from uhashring import HashRing
from app.core.hashring import HashRing
from app.core.config import NODE_ID, VNODES
import hashlib
import pickle
from copy import deepcopy

def hash_key(key: str) -> int:
    return int(hashlib.sha256(key.encode()).hexdigest(), 16)

def custom_hash(key):
    # Check if the input is already a valid SHA256 hash (64-character hex string)
    if isinstance(key, str) and len(key) == 64 and all(c in '0123456789abcdef' for c in key.lower()):
        return int(key, 16)  # Convert the hex string to an integer
    else:
        # For nodes like 'node1', hash them using their own hash function
        return hash_key(key)
class ConsistentHashManager:
    """Manages consistent hashing and node operations."""
    def __init__(self, nodes: List[str], node_id: str):
        self.node_id = node_id
        self.hash_ring = HashRing(nodes=nodes, hash_fn=custom_hash, vnodes=VNODES, replicas=4)
        self.pending_transfers: Dict[str, Set[str]] = {}  # Track pending transfers for new nodes
        self.node_key_map = defaultdict(set)  # Tracks keys assigned to each node
        self.ver = 0  # Version number for the hash ring

    def add_node(self, new_node: str) -> Set[str]:
        """
        Adds a new node to the hash ring and determines the keys to transfer to the new node.
        """
        print(f"Adding node {new_node}...")
        
        # old_hash_ring = HashRing(nodes=self.hash_ring.nodes)
        old_hash_ring = deepcopy(self.hash_ring)
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

    def get_node_key_map(self) -> Dict[str, Set[str]]:
        return dict(self.node_key_map)

    def get_pending_transfers(self, node: str) -> Set[str]:
        return self.pending_transfers.get(node, set())
    
    def get_ring_state(self) -> bytes:
        return pickle.dumps((self.hash_ring.nodes, self.node_key_map, self.ver))


hash_manager = ConsistentHashManager(nodes=[NODE_ID], node_id=NODE_ID)