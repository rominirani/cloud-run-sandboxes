FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    bash \
    tar \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf $(which python3) /usr/bin/python3

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY detonator.py .
COPY sample_payloads/ ./sample_payloads/

ENV PORT=8080
EXPOSE 8080

CMD ["python3", "detonator.py"]
