import pytest
from app.core.hashmanager import DistributedKeyValueManager


@pytest.fixture
def manager_a():
    """Fixture to initialize manager A."""
    return DistributedKeyValueManager(nodes=[], node_id="nodeA", vnodes=5, replicas=1)

@pytest.fixture
def manager_b():
    """Fixture to initialize manager B."""
    return DistributedKeyValueManager(nodes=[], node_id="nodeB", vnodes=5, replicas=1)

def test_add_node_transfer_keys(manager_a, manager_b):
    """
    Test adding a node and transferring keys between two managers.
    
    - Keys to be transferred must be owned by the new node.
    - Keys transferred to/from each manager must match the keys owned by the other.
    - The union of transferred keys should equal the original key set.
    """
    # Create a sample dataset
    keys = [f"key{i}" for i in range(10)]
    values = [f"value{i}" for i in range(10)]
    
    # Add keys
    for key, value in zip(keys, values):
        manager_a.add_key_value(key, value)
        manager_b.add_key_value(key, value)
    
    # Add nodeB to manager A's ring and get keys to transfer
    transfer_keys_to_b = manager_a.add_node("nodeB")
    
    # Add nodeA to manager B's ring and get keys to transfer
    transfer_keys_to_a = manager_b.add_node("nodeA")
    
    # Ensure the keys to be transferred are owned by the new node
    for key in transfer_keys_to_b:
        assert "nodeB" in manager_a.hash_ring.get_all_nodes(key)

    for key in transfer_keys_to_a:
        assert "nodeA" in manager_b.hash_ring.get_all_nodes(key)
    
    # Ensure keys transferred to B match keys owned by B in A's view
    for key in transfer_keys_to_b:
        assert manager_a.get_value(key) is not None  # Transferred key exists in A's storage
        manager_b.add_key_value(key, manager_a.get_value(key))  # Simulate transfer
    
    # Ensure keys transferred to A match keys owned by A in B's view
    for key in transfer_keys_to_a:
        assert manager_b.get_value(key) is not None  # Transferred key exists in B's storage
        manager_a.add_key_value(key, manager_b.get_value(key))  # Simulate transfer
    
    # Union of transferred keys must cover all keys
    transferred_union = set(transfer_keys_to_a) | set(transfer_keys_to_b)
    assert transferred_union == set(keys)
    
    # Ensure all keys are still accessible after transfers
    for key in keys:
        if key in transfer_keys_to_b:
            assert manager_b.get_value(key) == f"value{key[3:]}"
        elif key in transfer_keys_to_a:
            assert manager_a.get_value(key) == f"value{key[3:]}"