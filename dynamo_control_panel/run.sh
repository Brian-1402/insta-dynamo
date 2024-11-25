#/bin/bash
pip install -r requirements.txt
uvicorn src.api.endpoints:app --host localhost --port 8000 --reload