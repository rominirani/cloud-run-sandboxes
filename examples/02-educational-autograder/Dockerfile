FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    bash \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf $(which python3) /usr/bin/python3

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY autograder.py .
COPY test_suite/ ./test_suite/
COPY sample_submissions/ ./sample_submissions/

ENV PORT=8080
EXPOSE 8080

CMD ["python3", "autograder.py"]
