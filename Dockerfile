# Use Python 3.13 slim image (smaller, faster)
FROM python:3.13-slim

# Set working directory inside container
WORKDIR /app

# Install system dependencies if needed
# RUN apt-get update && apt-get install -y \
#     gcc \
#     && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port (for future API)
EXPOSE 8000

# Default command (will be overridden by docker-compose)
CMD ["python", "src/main.py"]

