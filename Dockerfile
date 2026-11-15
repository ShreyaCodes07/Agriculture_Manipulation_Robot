FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy source tree
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY main.py ./

# Set environment
ENV PYTHONPATH=/app/backend
ENV PORT=8000
ENV MODE=simulation

EXPOSE 8000

# Start server
CMD ["sh", "-c", "python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
