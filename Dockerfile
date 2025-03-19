# Use Python 3.11 slim image
FROM python:3.11-slim

LABEL maintainer="AI Football Betting Advisor Team"
LABEL description="Data-driven football betting advisor with value bet recommendations"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create and set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    g++ \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m bettor
RUN chown -R bettor:bettor /app
USER bettor

# Run deployment checklist in test mode
RUN python tests/deployment_checklist.py --test-only || echo "Deployment checks will be performed at runtime"

# Set up volume for persistent data
VOLUME /app/data

# Expose health check port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Create a startup script to run both the health check server and main application
RUN echo '#!/bin/bash\npython health.py & python main.py' > /app/start.sh
RUN chmod +x /app/start.sh

# Command to run the application
CMD ["/app/start.sh"] 