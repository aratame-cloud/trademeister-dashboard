# Trademeister Market Dashboard - Ultra-Lightweight Production Container
FROM python:3.11-slim

WORKDIR /app

# Prevent Python from writing .pyc and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install runtime dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY server.py dashboard_v2.html index.html ./

# Expose server port
EXPOSE 8080

# Run lightweight server
CMD ["python3", "server.py"]
