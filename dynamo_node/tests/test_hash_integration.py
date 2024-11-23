import pytest
from app.core.hashing import ConsistentHashManager

@pytest.fixture
def setup_hash_manager():
    """Fixture to set up a ConsistentHashManager with some initial nodes."""
    nodes = ["node1", "node2", "node3"]
    return ConsistentHashManager(nodes=nodes, node_id="node1")

@pytest.fixture
def generate_keys():
    """Fixture to generate random keys for testing."""
    import random, string
    random.seed(42)

    def _generate(num_keys, length=8):
        return [''.join(random.choices(string.ascii_letters + string.digits, k=length)) for _ in range(num_keys)]

    return _generate

def test_initial_distribution(setup_hash_manager, generate_keys):
    """Test initial key distribution across nodes."""
    hash_manager = setup_hash_manager
    keys = generate_keys(100)
    for key in keys:
        hash_manager.assign_key(key)
    hash_manager.print_node_key_distribution()

    # Verify key assignment to nodes
    total_keys = sum(len(keys) for keys in hash_manager.node_key_map.values())
    assert total_keys == 100, "All keys should be assigned initially"

def test_add_node(setup_hash_manager, generate_keys):
    """Test adding a new node and redistribution of keys."""
    hash_manager = setup_hash_manager
    keys = generate_keys(100)
    for key in keys:
        hash_manager.assign_key(key)

    new_node = "node4"
    transferred_keys = hash_manager.add_node(new_node)
    hash_manager.print_node_key_distribution()

    # Check if keys are transferred
    assert len(transferred_keys) > 0, "Keys should be transferred to the new node"
    assert len(hash_manager.node_key_map[new_node]) == len(transferred_keys), "Transferred keys should match new node's assigned keys"

def test_remove_node(setup_hash_manager, generate_keys):
    """Test removing a node and redistribution of keys."""
    hash_manager = setup_hash_manager
    keys = generate_keys(100)
    for key in keys:
        hash_manager.assign_key(key)

    node_to_remove = "node2"
    hash_manager.remove_node(node_to_remove)
    hash_manager.print_node_key_distribution()

    # Verify that the removed node no longer exists
    assert node_to_remove not in hash_manager.node_key_map, "Removed node should not exist in the key map"

def test_key_reassignment_after_node_removal(setup_hash_manager, generate_keys):
    """Test if keys are reassigned correctly after node removal."""
    hash_manager = setup_hash_manager
    keys = generate_keys(100)
    for key in keys:
        hash_manager.assign_key(key)

    node_to_remove = "node3"
    old_keys = hash_manager.node_key_map[node_to_remove].copy()
    hash_manager.remove_node(node_to_remove)

    for key in old_keys:
        responsible_node = hash_manager.hash_ring.get_node(key)
        assert responsible_node != node_to_remove, f"Key {key} should not map to the removed node"

def test_pending_transfers_on_addition(setup_hash_manager, generate_keys):
    """Test tracking of pending transfers when a node is added."""
    hash_manager = setup_hash_manager
    keys = generate_keys(100)
    for key in keys:
        hash_manager.assign_key(key)

    new_node = "node4"
    hash_manager.add_node(new_node)
    pending_transfers = hash_manager.get_pending_transfers(new_node)

    assert len(pending_transfers) > 0, "There should be pending transfers for the new node"
    assert all(key in hash_manager.node_key_map[new_node] for key in pending_transfers), "Transferred keys should be assigned to the new node"

def test_edge_case_empty_hash_ring():
    """Test behavior when hash ring starts empty."""
    hash_manager = ConsistentHashManager(nodes=[], node_id="node1")

    # Adding a node to an empty ring
    hash_manager.add_node("node1")
    assert "node1" in hash_manager.hash_ring.nodes, "Node1 should be added to an empty hash ring"

def test_duplicate_node_addition(setup_hash_manager):
    """Test adding a duplicate node."""
    hash_manager = setup_hash_manager
    initial_nodes = set(hash_manager.hash_ring.nodes)
    hash_manager.add_node("node1")  # Adding a node that already exists

    assert set(hash_manager.hash_ring.nodes) == initial_nodes, "Duplicate nodes should not be added"

def test_nonexistent_node_removal(setup_hash_manager):
    """Test removing a nonexistent node."""
    hash_manager = setup_hash_manager

    with pytest.raises(ValueError, match="Node nonexistent_node not in hash ring."):
        hash_manager.remove_node("nonexistent_node")