# Google Cloud Run Sandboxes: Hands-On Guide & End-to-End Examples

This repository contains a comprehensive guide and four production-grade reference implementations for **Google Cloud Run Sandboxes** (Public Preview).

Cloud Run Sandboxes provide native, sub-second, micro-isolated execution boundaries directly inside your second-generation Cloud Run container instances.

---

## 📖 Complete Tutorial

The complete, publication-grade tutorial is available in **[`TUTORIAL.md`](TUTORIAL.md)**.

It covers:
1. **Introduction**: The shift to AI execution planes and in-instance sandboxing.
2. **Why Cloud Run Sandboxes?**: The security triad (credential isolation, deny-by-default egress, read-only root with tmpfs overlay).
3. **Step-by-Step Guide**: Configuring `gcloud beta run deploy --sandbox-launcher` and using `/usr/local/gcp/bin/sandbox`.
4. **101 Example**: Minimal safe code runner microservice.
5. **3 End-to-End Real-World Use Cases**:
   - Educational Autograder & Competitive Programming Judge
   - AI-Assisted Autonomous Web Scraper & Research Agent
   - SecOps Incident Response & Malware Payload Detonator
6. **Best Practices & Operational Checklist**: Resource sizing, timeouts, and daemon modes.
7. **References & Further Reading**: Links and attributions to the foundational blog posts and documentation.

---

## 📂 Repository Structure

```text
cloud-run-sandboxes/
├── TUTORIAL.md                          # Full comprehensive tutorial with Mermaid diagrams
├── README.md                            # Repository index & quickstart instructions
└── examples/
    ├── 01-hello-sandbox-101/            # 101 Getting Started code execution service
    │   ├── main.py                      # FastAPI code runner + security probe endpoints
    │   ├── Dockerfile                   # Python 3.11-slim runtime container
    │   ├── requirements.txt             # Dependencies (FastAPI, uvicorn, pydantic)
    │   └── deploy.sh                    # One-click deployment script
    │
    ├── 02-educational-autograder/       # Use Case 1: Code judge & autograder
    │   ├── autograder.py                # FastAPI submission grading orchestrator
    │   ├── test_suite/runner.py         # Hidden test suite runner
    │   ├── sample_submissions/          # Correct, timeout, and malicious exploit solutions
    │   ├── Dockerfile
    │   ├── requirements.txt
    │   └── deploy.sh
    │
    ├── 03-autonomous-web-scraper/       # Use Case 2: Isolated web scraping agent
    │   ├── scraper_agent.py             # Web scraper with --allow-egress & SSRF protection
    │   ├── Dockerfile
    │   ├── requirements.txt
    │   └── deploy.sh
    │
    └── 04-secops-payload-detonator/     # Use Case 3: Threat hunting & malware sandbox
        ├── detonator.py                 # Detached sandbox manager & tar forensic scanner
        ├── sample_payloads/             # Harmless simulated ransomware dropper
        ├── Dockerfile
        ├── requirements.txt
        └── deploy.sh
```

---

## 🚀 Quickstart: Deploying the 101 Example

### 1. Prerequisites
- Google Cloud SDK with `beta` components:
  ```bash
  gcloud components install beta
  ```
- Second-generation Cloud Run service enabled.

### 2. Deploy
Navigate to the 101 example and deploy:
```bash
cd examples/01-hello-sandbox-101
chmod +x deploy.sh
./deploy.sh
```

Or deploy manually via `gcloud`:
```bash
gcloud beta run deploy sandbox-hello-101 \
    --source examples/01-hello-sandbox-101 \
    --region us-central1 \
    --execution-environment gen2 \
    --sandbox-launcher \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1
```

### 3. Test Invocations

#### Safe Python Execution:
```bash
curl -X POST https://<YOUR-SERVICE-URL>/run \
  -H "Content-Type: application/json" \
  -d '{"language": "python", "code": "print(2 ** 32)"}'
```

#### Test Metadata Isolation:
```bash
curl -X POST https://<YOUR-SERVICE-URL>/test/metadata-isolation
```

#### Test Environment Variable Shielding:
```bash
curl -X POST https://<YOUR-SERVICE-URL>/test/env-isolation
```
