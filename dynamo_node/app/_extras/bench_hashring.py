import random
from typing import Dict, Set, List
import string
from collections import defaultdict

import sys
app_path = "./../"
sys.path.append(app_path)

from app.core.hashing import ConsistentHashManager

random.seed(42)
def generate_random_keys(num_keys: int, length: int = 8) -> List[str]:
    """Generate a list of random alphanumeric keys."""
    return [''.join(random.choices(string.ascii_letters + string.digits, k=length)) for _ in range(num_keys)]


def benchmark_hash_ring():
    """Benchmark function for consistent hashing."""
    initial_nodes = ["node1", "node2", "node3"]
    main_node = "node1"
    hash_manager = ConsistentHashManager(nodes=initial_nodes, node_id=main_node)

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
        print(f"Keys transferred from {main_node} to {node}: {len(keys)}")
        assert len(keys) == len(transferred_keys)


# Run the benchmark
if __name__ == "__main__":
    benchmark_hash_ring()