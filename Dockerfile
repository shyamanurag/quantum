# NUCLEAR MINIMAL - BYPASS SNAPSHOT FAILURE
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 && rm -rf /var/lib/apt/lists/*

# Install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy main app file
COPY app.py .

# Copy ALL source code (required for app.py imports)
COPY src/ src/

# Copy configuration files
COPY config/ config/

# User setup
RUN useradd app && chown -R app:app /app
USER app

EXPOSE 8000

CMD ["python", "app.py"]
