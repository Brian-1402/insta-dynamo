import os
from dotenv import load_dotenv

# Load environment variables from `.env` file
load_dotenv()

# Access environment variables
NODE_ID = os.getenv("NODE_ID", "default_node")  # Default value if not set
VNODES = int(os.getenv("VNODES", "10"))  # Default value if not set
STORE_DIR = os.getenv("STORE", "./store")          # Default to ./store

# Add other configuration variables as needed
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")