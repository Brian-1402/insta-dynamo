import pytest
from app.core.hashing import ConsistentHashManager
from uhashring import HashRing

NODE_ID = "node1"  # Mocked node ID for testing

@pytest.fixture
def setup_hash_manager():
    """Fixture to set up a ConsistentHashManager instance with mock nodes."""
    nodes = ["node1", "node2", "node3"]
    manager = ConsistentHashManager(nodes=nodes, node_id=NODE_ID)
    return manager

def test_initial_node_distribution(setup_hash_manager):
    """Test initial key distribution among nodes."""
    manager = setup_hash_manager
    test_keys = ["key1", "key2", "key3", "key4"]
    for key in test_keys:
        manager.assign_key(key)
    
    assert sum(len(keys) for keys in manager.node_key_map.values()) == len(test_keys)
    assert all(key in manager.node_key_map[manager.hash_ring.get_node(key)] for key in test_keys)

def test_add_node_updates_distribution(setup_hash_manager):
    """Test adding a node and the re-distribution of keys."""
    manager = setup_hash_manager
    test_keys = ["key1", "key2", "key3", "key4"]
    for key in test_keys:
        manager.assign_key(key)

    new_node = "node4"
    transfer_keys = manager.add_node(new_node)

    # Validate the keys were correctly reassigned
    for key in transfer_keys:
        assert manager.hash_ring.get_node(key) == new_node
        assert key in manager.node_key_map[new_node]

    # Ensure keys are no longer assigned to the original node
    for key in transfer_keys:
        assert key not in manager.node_key_map[NODE_ID]

def test_remove_node_reassigns_keys(setup_hash_manager):
    """Test removing a node and reassigning its keys."""
    manager = setup_hash_manager
    manager.assign_key("key1")
    manager.assign_key("key2")

    manager.add_node("node4")
    removed_node = "node2"
    if removed_node in manager.hash_ring.nodes:
        manager.remove_node(removed_node)

    # Ensure the removed node is no longer in the ring
    assert removed_node not in manager.hash_ring.nodes

    # Ensure keys handled by the removed node are reassigned
    for key in manager.node_key_map[removed_node]:
        responsible_node = manager.hash_ring.get_node(key)
        assert responsible_node != removed_node
        assert key in manager.node_key_map[responsible_node]

def test_get_pending_transfers(setup_hash_manager):
    """Test retrieving pending transfers for a node."""
    manager = setup_hash_manager
    test_keys = ["key1", "key2", "key3"]
    for key in test_keys:
        manager.assign_key(key)

    new_node = "node4"
    manager.add_node(new_node)
    pending_transfers = manager.get_pending_transfers(new_node)

    assert pending_transfers == manager.pending_transfers[new_node]
    assert all(key in pending_transfers for key in manager.node_key_map[new_node])

def test_empty_node_removal(setup_hash_manager):
    """Test removing a node without any keys."""
    manager = setup_hash_manager
    manager.add_node("node4")
    manager.remove_node("node4")

    assert "node4" not in manager.hash_ring.nodes
    assert "node4" not in manager.pending_transfers
    assert "node4" not in manager.node_key_map