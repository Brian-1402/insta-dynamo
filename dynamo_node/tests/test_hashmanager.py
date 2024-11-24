import pytest
from app.core.hashmanager import DistributedKeyValueManager
from app.core.hashring import HashRing

NODE_ID = "node1"
VNODES = 5
N_REPLICAS = 3

@pytest.fixture
def manager():
    """Fixture to initialize a DistributedKeyValueManager."""
    nodes = [NODE_ID]
    return DistributedKeyValueManager(nodes=nodes, node_id=NODE_ID, vnodes=VNODES, replicas=N_REPLICAS)

def test_add_key_value(manager):
    """Test adding a key-value pair."""
    key, value = "key1", "value1"
    manager.add_key_value(key, value)
    assert manager.get_value(key) == value

def test_add_key_value_invalid_node(manager):
    """Test adding a key-value pair to a node not responsible for the key."""
    key, value = "key2", "value2"
    manager.node_id = "other_node"
    response = manager.add_key_value(key, value)
    assert response[0] == False

def test_get_value_nonexistent_key(manager):
    """Test retrieving a value for a non-existent key."""
    key = "nonexistent"
    assert manager.get_value(key) is None

def test_remove_key(manager):
    """Test removing a key."""
    key, value = "key3", "value3"
    manager.add_key_value(key, value)
    manager.remove_key(key)
    assert manager.get_value(key) is None

def test_list_local_keys(manager):
    """Test listing all locally stored keys."""
    keys = ["key4", "key5", "key6"]
    for key in keys:
        manager.add_key_value(key, f"value_for_{key}")
    local_keys = manager.list_local_keys()
    assert set(local_keys) == set(keys)

def test_reset(manager):
    """Test resetting the manager."""
    key, value = "key9", "value9"
    manager.add_key_value(key, value)
    manager.reset()
    assert manager.get_value(key) is None
    assert manager.list_local_keys() == []

def test_export_ring(manager):
    """Test exporting hash ring metadata."""
    metadata = manager.export_ring()
    assert metadata["physical_nodes"] == {NODE_ID: VNODES}

def test_reconstruct(manager):
    """Test reconstructing a manager from metadata."""
    key, value = "key10", "value10"
    manager.add_key_value(key, value)
    metadata = manager.export_ring()
    reconstructed_manager = DistributedKeyValueManager.reconstruct(metadata, node_id=NODE_ID)
    assert reconstructed_manager.get_value(key) is None
    assert reconstructed_manager.hash_ring.ring == manager.hash_ring.ring

def test_add_multiple_nodes(manager):
    """Test adding multiple nodes and ensuring proper key distribution."""
    nodes = ["node2", "node3", "node4"]
    for node in nodes:
        manager.add_node(node)
    for key in ["key11", "key12", "key13"]:
        responsible_nodes = manager.hash_ring.get_all_nodes(key)
        assert len(set(responsible_nodes)) == min(N_REPLICAS, 3)

def test_pending_transfers(manager):
    """Test that pending transfers are recorded correctly."""
    new_node = "node5"
    for i in range(0,100):
        manager.add_key_value(f"key{i}", f"value{i}")
    transferred1 = manager.add_node("node5")
    transferred2 = manager.add_node("node6")
    transferred3 = manager.add_node("node7")
    # first 2 should be empty, 3rd should be non empty
    assert len(transferred1) == 0 and len(transferred2) == 0
    assert len(transferred3) != 0 
    assert manager.pending_transfers["node5"] == transferred1
    assert manager.pending_transfers["node6"] == transferred2
    assert manager.pending_transfers["node7"] == transferred3

def test_reconstruction_with_pending_transfers():
    """Test reconstruction with pending transfers."""
    nodes = [NODE_ID, "node6"]
    manager = DistributedKeyValueManager(nodes=nodes, node_id=NODE_ID)
    key, value = "key15", "value15"
    manager.add_key_value(key, value)
    metadata = manager.export_ring()
    reconstructed_manager = DistributedKeyValueManager.reconstruct(metadata, node_id=NODE_ID)
    assert reconstructed_manager.pending_transfers == {}