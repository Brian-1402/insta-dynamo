#/bin/bash
pip install -r ../requirements.txt
python ./initialize_db.py
uvicorn app:app --host 0.0.0.0 --port 9000 --reload
