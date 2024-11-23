from typing import Dict, Set, List

class KeyValueStorage:
    """Handles key-value storage and retrieval."""
    def __init__(self):
        self.store: Dict[str, str] = {}

    def add(self, key: str, value: str):
        self.store[key] = value

    def get(self, key: str) -> str:
        return self.store.get(key)

    def remove(self, key: str):
        if key in self.store:
            del self.store[key]
    
    def clear(self):
        self.store.clear()

    def list_keys(self) -> List[str]:
        return list(self.store.keys())

kv_storage = KeyValueStorage()