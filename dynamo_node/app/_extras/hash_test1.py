from uhashring import HashRing
import hashlib

def hash_key(key: str) -> int:
    return int(hashlib.sha256(key.encode()).hexdigest(), 16)

# Define a custom hash function
def custom_hash(key):
    # Check if the input is already a valid SHA256 hash (64-character hex string)
    if isinstance(key, str) and len(key) == 64 and all(c in '0123456789abcdef' for c in key.lower()):
        return int(key, 16)  # Convert the hex string to an integer
    else:
        # For nodes like 'node1', hash them using their own hash function (e.g., built-in hash)
        return hash(key)

# Initialize the consistent hash ring with the custom hash function
hr = HashRing(nodes=['node1', 'node2', 'node3'], hash_fn='ketama', replicas=4)

# Provide the SHA256 hash as the key directly
key = "key1"  # Example SHA256 hash
print(hr.get_node(key))
print(hr.distribution)