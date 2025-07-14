# syntax=docker/dockerfile:1

FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc \
 && rm -rf /var/lib/apt/lists/*

# Copy & install Python deps (including uvicorn)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code, data, faiss_index.pkl, etc.
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Launch Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
