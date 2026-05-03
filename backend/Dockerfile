# PRODUCTION BACKEND DOCKERFILE
FROM python:3.12-slim

# Prevent python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

WORKDIR /app

# Install system dependencies for PyMuPDF and other libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libmupdf-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir gunicorn uvicorn


# Copy application code
COPY . .

# Run with Gunicorn for production concurrency
CMD gunicorn -c gunicorn_conf.py main:app
