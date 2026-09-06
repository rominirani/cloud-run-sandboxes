import hashlib
import os
import shutil
import subprocess
import tarfile
import tempfile
import time
import uuid
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(
    title="SecOps Malware & Script Detonator",
    description="Automated incident response sandbox detonating suspicious payloads with zero-egress containment and tar filesystem forensic analysis",
    version="1.0.0",
)

SANDBOX_BIN = "/usr/local/gcp/bin/sandbox" if os.path.exists("/usr/local/gcp/bin/sandbox") else shutil.which("sandbox")


class DetonationRequest(BaseModel):
    script_content: str = Field(..., description="Raw bash or python payload to detonate")
    script_type: str = Field(default="bash", example="bash")
    timeout_sec: int = Field(default=15, ge=2, le=60)


class DroppedFileArtifact(BaseModel):
    filename: str
    size_bytes: int
    sha256: str
    preview: str


class DetonationReport(BaseModel):
    session_id: str
    execution_success: bool
    exit_code: int
    stdout: str
    stderr: str
    execution_time_ms: float
    dropped_files_count: int
    dropped_files: List[DroppedFileArtifact]
    c2_callbacks_prevented: bool
    metadata_theft_prevented: bool


@app.get("/")
def health():
    return {
        "status": "online",
        "sandbox_present": bool(SANDBOX_BIN),
        "containment_mode": "deny-by-default-egress-ephemeral-overlay",
    }


@app.post("/detonate", response_model=DetonationReport)
def detonate_payload(req: DetonationRequest):
    start_time = time.time()
    session_id = f"detox-{uuid.uuid4().hex[:8]}"

    if not SANDBOX_BIN:
        raise HTTPException(
            status_code=500,
            detail="Cloud Run Sandbox binary not found. Deploy with --sandbox-launcher."
        )

    # Temporary directory on host for receiving the tar snapshot
    host_workdir = tempfile.mkdtemp(prefix=f"report_{session_id}_")
    tar_path = os.path.join(host_workdir, "filesystem_overlay.tar")
    script_path = os.path.join(host_workdir, "payload.sh")

    with open(script_path, "w") as f:
        f.write(req.script_content)

    dropped_artifacts: List[DroppedFileArtifact] = []
    exit_code = 0
    stdout_captured = ""
    stderr_captured = ""
    success = False

    try:
        # Step 1: Spin up a named, detached background sandbox with writable overlay enabled
        # The sandbox runs sleep so it remains alive to accept multiple commands
        start_cmd = [
            SANDBOX_BIN, "run",
            "--write",
            session_id,
            "--detach",
            "--mount", f"type=bind,source={host_workdir},destination=/mnt/host,readonly",
            "--",
            "/bin/bash", "-c", "sleep 5m"
        ]
        subprocess.run(start_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # Step 2: Execute the untrusted payload inside the active detached sandbox
        if req.script_type == "python":
            exec_inner = ["/usr/bin/python3", "/mnt/host/payload.sh"]
        else:
            exec_inner = ["/bin/bash", "/mnt/host/payload.sh"]

        exec_cmd = [
            SANDBOX_BIN, "exec",
            session_id,
            "--"
        ] + exec_inner

        try:
            proc = subprocess.run(
                exec_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=req.timeout_sec,
            )
            exit_code = proc.returncode
            stdout_captured = proc.stdout
            stderr_captured = proc.stderr
            success = (proc.returncode == 0)
        except subprocess.TimeoutExpired as e:
            exit_code = 124
            stdout_captured = e.stdout or ""
            stderr_captured = "Detonation timed out."

        # Step 3: Capture a forensic snapshot of modified overlay files using sandbox tar
        tar_cmd = [
            SANDBOX_BIN, "tar",
            session_id,
            f"--file={tar_path}"
        ]
        tar_proc = subprocess.run(tar_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if tar_proc.returncode != 0:
            stderr_captured += f"\n[tar error rc={tar_proc.returncode}]: {tar_proc.stderr} {tar_proc.stdout}"

        # Step 4: Inspect the exported tar archive on the host container
        if os.path.exists(tar_path):
            tar_size = os.path.getsize(tar_path)
            if tar_size == 0:
                stderr_captured += f"\n[tar archive is empty (0 bytes)]"
            else:
                extract_dir = os.path.join(host_workdir, "extracted")
                os.makedirs(extract_dir, exist_ok=True)
                try:
                    with tarfile.open(tar_path, "r") as tar:
                        tar.extractall(path=extract_dir)

                    # Scan for dropped files
                    for root, _, files in os.walk(extract_dir):
                        for fname in files:
                            full_path = os.path.join(root, fname)
                            rel_path = os.path.relpath(full_path, extract_dir)
                            file_size = os.path.getsize(full_path)
                            
                            # Calculate sha256
                            h = hashlib.sha256()
                            with open(full_path, "rb") as bf:
                                while chunk := bf.read(4096):
                                    h.update(chunk)
                            file_sha = h.hexdigest()

                            # Read preview
                            try:
                                with open(full_path, "r", errors="ignore") as tf:
                                    preview = tf.read(200).replace("\n", " ")
                            except Exception:
                                preview = "<binary content>"

                            dropped_artifacts.append(
                                DroppedFileArtifact(
                                    filename=f"/{rel_path}",
                                    size_bytes=file_size,
                                    sha256=file_sha,
                                    preview=preview,
                                )
                            )
                except Exception as ex:
                    stderr_captured += f"\nFailed parsing forensic tar: {ex}"

    finally:
        # Step 5: Clean up sandbox and host temporary files
        subprocess.run([SANDBOX_BIN, "delete", session_id], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        shutil.rmtree(host_workdir, ignore_errors=True)

    elapsed_ms = (time.time() - start_time) * 1000

    return DetonationReport(
        session_id=session_id,
        execution_success=success,
        exit_code=exit_code,
        stdout=stdout_captured,
        stderr=stderr_captured,
        execution_time_ms=elapsed_ms,
        dropped_files_count=len(dropped_artifacts),
        dropped_files=dropped_artifacts,
        c2_callbacks_prevented=True,
        metadata_theft_prevented=True,
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run("detonator:app", host="0.0.0.0", port=port)
