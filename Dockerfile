# NUCLEAR MINIMAL - BYPASS SNAPSHOT FAILURE
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 && rm -rf /var/lib/apt/lists/*

# Install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy ONLY core app file
COPY app.py .

# Create minimal directory structure
RUN mkdir -p src/api src/core src/config config logs

# Copy only essential files one by one
COPY src/__init__.py src/
COPY src/config/__init__.py src/config/
COPY src/config/database.py src/config/
COPY src/core/__init__.py src/core/
COPY src/core/config.py src/core/

# Essential config (if exists)
COPY config/config.yaml config/

# User setup
RUN useradd app && chown -R app:app /app
USER app

EXPOSE 8000

CMD ["python", "app.py"]
