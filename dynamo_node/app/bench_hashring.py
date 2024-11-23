import random
from uhashring import HashRing
from typing import Dict, Set, List
import string
from collections import defaultdict

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


random.seed(42)
def generate_random_keys(num_keys: int, length: int = 8) -> List[str]:
    """Generate a list of random alphanumeric keys."""
    return [''.join(random.choices(string.ascii_letters + string.digits, k=length)) for _ in range(num_keys)]


def benchmark_hash_ring():
    """Benchmark function for consistent hashing."""
    initial_nodes = ["node1", "node2", "node3"]
    hash_manager = ConsistentHashManager(nodes=initial_nodes, node_id="node1")

    # Generate random keys and assign them
    num_keys = 1000
    keys = generate_random_keys(num_keys)
    for key in keys:
        hash_manager.assign_key(key)

    print("Initial Key Distribution:")
    hash_manager.print_node_key_distribution()

    # Add a new node and observe redistribution
    new_node = "node4"
    print(f"\nAdding new node: {new_node}")
    transferred_keys = hash_manager.add_node(new_node)

    print(f"\nKeys transferred to {new_node}: {len(transferred_keys)}")
    hash_manager.print_node_key_distribution()

    # List keys transferred from other nodes
    for node, keys in hash_manager.pending_transfers.items():
        print(f"Keys transferred from {node} to {new_node}: {len(keys)}")


# Run the benchmark
if __name__ == "__main__":
    benchmark_hash_ring()