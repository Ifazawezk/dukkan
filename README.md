# Dukkan

Inventory and point-of-sale system for small shops in Qatar and the Gulf.

Work in progress. The backend is a FastAPI application in `backend/`.

## Running the backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000/docs.

## Tests

```bash
cd backend
pytest
```
