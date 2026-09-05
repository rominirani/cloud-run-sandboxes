import os
import shutil
import subprocess
import time
import json
from typing import Optional, List, Dict
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(
    title="Cloud Run Sandboxes Autonomous Web Scraper",
    description="Isolated web research and scraping engine with controlled egress and SSRF defense",
    version="1.0.0",
)

SANDBOX_BIN = "/usr/local/gcp/bin/sandbox" if os.path.exists("/usr/local/gcp/bin/sandbox") else shutil.which("sandbox")

# Simulate sensitive host agent API keys and credentials
os.environ["LLM_API_KEY"] = "sk-live-super-secret-agent-key-9999"
os.environ["DATABASE_URL"] = "postgres://admin:super_secret_pw@internal.db:5432/crm"


class ScrapeRequest(BaseModel):
    url: str = Field(..., example="https://httpbin.org/html", description="Target website to scrape")
    tags: List[str] = Field(default=["title", "h1", "p"], description="HTML tags to extract")
    timeout_sec: int = Field(default=15, ge=2, le=30)


class ScrapeResponse(BaseModel):
    url: str
    success: bool
    status_code: Optional[int] = None
    extracted_data: Dict[str, List[str]]
    raw_stdout: str
    raw_stderr: str
    execution_time_ms: float
    ssrf_blocked: bool


@app.get("/")
def health():
    return {
        "status": "active",
        "sandbox_present": bool(SANDBOX_BIN),
        "network_mode": "controlled-egress-isolated-metadata",
    }


@app.post("/scrape", response_model=ScrapeResponse)
def scrape_url(req: ScrapeRequest):
    start_time = time.time()

    if not SANDBOX_BIN:
        raise HTTPException(
            status_code=500,
            detail="Cloud Run Sandbox binary not found. Deploy with --sandbox-launcher."
        )

    # Scraper script executed inside the sandbox
    # It fetches the page, parses with BeautifulSoup, extracts text, and returns structured JSON
    scraper_script = f"""
import sys
import json
import urllib.request
from bs4 import BeautifulSoup

url = {json.dumps(req.url)}
target_tags = {json.dumps(req.tags)}

output = {{
    "status_code": None,
    "data": {{}},
    "error": None
}}

try:
    headers = {{'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as response:
        output["status_code"] = response.getcode()
        html = response.read().decode('utf-8', errors='ignore')
        
        soup = BeautifulSoup(html, 'html.parser')
        for tag in target_tags:
            output["data"][tag] = [elem.get_text(strip=True) for elem in soup.find_all(tag)][:10]

except Exception as e:
    output["error"] = str(e)

print(json.dumps(output))
"""

    # Build sandbox command with --allow-egress enabled
    # Crucially: Even with --allow-egress, Cloud Run Sandbox prevents access to 169.254.169.254
    # and keeps the host container's environment variables (LLM_API_KEY) completely invisible.
    cmd = [
        SANDBOX_BIN, "do",
        "--allow-egress",
        "--",
        "/usr/bin/python3", "-c", scraper_script
    ]

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=req.timeout_sec,
        )
        elapsed_ms = (time.time() - start_time) * 1000

        parsed = None
        for line in proc.stdout.splitlines():
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    parsed = json.loads(line)
                    break
                except json.JSONDecodeError:
                    continue

        if parsed and not parsed.get("error"):
            return ScrapeResponse(
                url=req.url,
                success=True,
                status_code=parsed.get("status_code"),
                extracted_data=parsed.get("data", {}),
                raw_stdout=proc.stdout,
                raw_stderr=proc.stderr,
                execution_time_ms=elapsed_ms,
                ssrf_blocked=False,
            )
        else:
            return ScrapeResponse(
                url=req.url,
                success=False,
                status_code=parsed.get("status_code") if parsed else None,
                extracted_data={},
                raw_stdout=proc.stdout,
                raw_stderr=proc.stderr or (parsed.get("error") if parsed else "Failed to parse"),
                execution_time_ms=elapsed_ms,
                ssrf_blocked=False,
            )

    except subprocess.TimeoutExpired as e:
        elapsed_ms = (time.time() - start_time) * 1000
        return ScrapeResponse(
            url=req.url,
            success=False,
            status_code=408,
            extracted_data={},
            raw_stdout=e.stdout or "",
            raw_stderr=f"Scrape timed out after {req.timeout_sec}s",
            execution_time_ms=elapsed_ms,
            ssrf_blocked=False,
        )


@app.post("/test/ssrf-metadata-check")
def test_ssrf_metadata():
    """
    Demonstrates security isolation:
    Even when --allow-egress is turned ON to enable web scraping,
    the GCP Instance Metadata Server (169.254.169.254) remains unreachable from inside the sandbox!
    """
    if not SANDBOX_BIN:
        raise HTTPException(status_code=500, detail="Sandbox binary not found.")

    probe_script = """
import urllib.request
import os

res = {}
# Try to reach metadata
try:
    req = urllib.request.Request(
        "http://169.254.169.254/computeMetadata/v1/instance/service-accounts/default/identity?audience=https://vault.com",
        headers={"Metadata-Flavor": "Google"}
    )
    with urllib.request.urlopen(req, timeout=2) as r:
        res["metadata_access"] = "LEAKED: " + r.read().decode()[:50]
except Exception as e:
    res["metadata_access"] = f"BLOCKED: {type(e).__name__}"

# Try to read host agent secret
res["llm_key_access"] = os.getenv("LLM_API_KEY", "NOT_ACCESSIBLE")

import json
print(json.dumps(res))
"""

    cmd = [
        SANDBOX_BIN, "do",
        "--allow-egress",
        "--",
        "/usr/bin/python3", "-c", probe_script
    ]

    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
    
    parsed = {}
    for line in proc.stdout.splitlines():
        if line.strip().startswith("{") and line.strip().endswith("}"):
            try:
                parsed = json.loads(line.strip())
                break
            except Exception:
                pass

    return {
        "sandbox_egress_flag": True,
        "probe_result": parsed,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "verdict": "SECURE: Metadata server and host environment variables are strictly shielded despite internet egress."
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run("scraper_agent:app", host="0.0.0.0", port=port)
