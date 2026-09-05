FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Ensure python3 is available at /usr/bin/python3 as well as /usr/local/bin/python3
RUN ln -sf $(which python3) /usr/bin/python3

WORKDIR /app

# Copy dependency definition and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY main.py .

# Expose standard Cloud Run port
ENV PORT=8080
EXPOSE 8080

CMD ["python3", "main.py"]
