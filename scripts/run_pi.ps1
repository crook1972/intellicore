python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn src.intellicore_backend.main:app --host 0.0.0.0 --port 8000
