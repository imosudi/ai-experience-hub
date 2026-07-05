# Use the official Python 3.12 slim image as base
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    PORT=5000

# Set work directory
WORKDIR /app

# Install system dependencies (build essentials, if any packages require compile steps)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml and source code
COPY pyproject.toml README.md /app/
COPY src /app/src
COPY app.py /app/

# Install the application and gunicorn production dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir . gunicorn

# Expose port
EXPOSE 5000

# Run using gunicorn in production
CMD gunicorn -w 4 -b 0.0.0.0:$PORT "app:app"
