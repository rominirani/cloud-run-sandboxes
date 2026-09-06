# Google Cloud Run Sandboxes: Hands-On Guide & End-to-End Examples

This repository contains the complete reference implementations, test suites, Dockerfiles, and deployment manifests for the hands-on guide published on the **Google Cloud Publication on Medium**:

👉 **[Safely Running Untrusted Code: A Hands-on Guide to Google Cloud Run Sandboxes](https://medium.com/google-cloud/safely-running-untrusted-code-a-hands-on-guide-to-google-cloud-run-sandboxes-8bbc95d391c7)**

Cloud Run Sandboxes provide native, sub-second, micro-isolated execution boundaries directly inside your second-generation Cloud Run container instances.

---

## 📖 Hands-On Guide & Architecture Breakdown

Read the full tutorial on Google Cloud Medium:  
🔗 **[Safely Running Untrusted Code: A Hands-on Guide to Google Cloud Run Sandboxes](https://medium.com/google-cloud/safely-running-untrusted-code-a-hands-on-guide-to-google-cloud-run-sandboxes-8bbc95d391c7)**

### Key Topics Covered in the Article:
1. **The Evolution of Compute Isolation**: From bare metal to in-container gVisor sandboxes.
2. **Why Cloud Run Sandboxes?**: The Zero-Trust Security Triad (credential isolation, deny-by-default egress, ephemeral root filesystem with tmpfs overlay).
3. **CLI Mechanics & Execution Modes**: One-shot (`sandbox do`) vs. stateful background daemons (`sandbox run` / `sandbox exec`).
4. **Filesystem & Storage Topologies**: tmpfs overlays, dual bind mounts, and `sandbox tar` forensic snapshots.
5. **A 101 Safe Code Execution Service**: FastAPI runner demonstrating dynamic binary detection, Pydantic input validation, and self-auditing security probes.
6. **Three Production Use Cases**:
   - **Educational Autograder & Competitive Programming Judge**: Dual read-only mounts, test-tampering defense, DoS loop termination.
   - **Autonomous Web Scraper & Research Agent**: Controlled egress (`--allow-egress`), metadata server (`169.254.169.254`) SSRF blocking, BeautifulSoup DOM parsing.
   - **SecOps Incident Response & Malware Detonator**: Detached daemon execution, forensic artifact export via `sandbox tar`, SHA-256 analysis.
7. **Production Best Practices & Checklist**: Resource sizing, cold-start amortization, and health checks.

---

## 📂 Repository Structure

```text
cloud-run-sandboxes/
├── README.md                            # Repository index, architecture & quickstart instructions
├── assets/                              # Architecture diagrams and visual artifacts
│   └── diagrams/
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
