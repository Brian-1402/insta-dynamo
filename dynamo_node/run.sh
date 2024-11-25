#/bin/bash
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 9090