# Builds the InForm API (backend/) together with the sibling inform package
# (src/) it imports at runtime — see backend/main.py's sys.path note — and the
# sample gallery data (data/samples/) that inform.samples reads from the repo
# root. Build context must be the repo root (not backend/) so all are reachable.
FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY src/ src/
COPY data/samples/ data/samples/

WORKDIR /app/backend

CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
