import os
import dotenv
from cryptography.fernet import Fernet

KEY_FILE = "key.key"

def generate_and_store_key():
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as key_file:
            key_file.write(key)
        print("Key generated and saved.")
    else:
        print("Key already exists.")

def load_key():
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as key_file:
            return Fernet(key_file.read())
    else:
        raise FileNotFoundError("Key file not found. Generate the key first.")

FERNET_KEY = os.getenv("FERNET_KEY")

if not FERNET_KEY:
    print("FERNET_KEY not found in environment variables. Generating a new key...")
    generate_and_store_key()
    FERNET_KEY = load_key()
    # Save in environment variables
    os.environ["FERNET_KEY"] = FERNET_KEY

fernet = Fernet(FERNET_KEY)

def encrypt_data(data: bytes) -> bytes:
    return fernet.encrypt(data)

def decrypt_data(data: bytes) -> bytes:
    return fernet.decrypt(data)

