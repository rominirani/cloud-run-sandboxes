import os
import shutil
import subprocess
import time
from typing import Optional, Literal
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(
    title="Cloud Run Sandbox 101 Runner",
    description="A secure, isolated execution endpoint running on Google Cloud Run Sandboxes",
    version="1.0.0",
)

SANDBOX_BIN = "/usr/local/gcp/bin/sandbox" if os.path.exists("/usr/local/gcp/bin/sandbox") else shutil.which("sandbox")


class ExecutionRequest(BaseModel):
    language: Literal["python", "bash"] = Field(default="python", description="Target execution runtime")
    code: str = Field(..., description="The code snippet to execute inside the sandbox")
    allow_write: bool = Field(default=False, description="Enable temporary writable tmpfs overlay (--write)")
    allow_egress: bool = Field(default=False, description="Enable external outbound networking (--allow-egress)")
    timeout_sec: int = Field(default=10, ge=1, le=60, description="Max execution timeout in seconds")


class ExecutionResponse(BaseModel):
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    execution_time_ms: float
    is_sandboxed: bool


def execute_in_sandbox(
    language: str,
    code: str,
    allow_write: bool = False,
    allow_egress: bool = False,
    timeout_sec: int = 10,
) -> ExecutionResponse:
    start_time = time.time()
    
    # Check if we are running in a Cloud Run instance with sandbox enabled
    if not SANDBOX_BIN:
        return ExecutionResponse(
            success=False,
            exit_code=-1,
            stdout="",
            stderr="ERROR: The 'sandbox' binary is not present. Ensure this service is deployed to Cloud Run with the --sandbox-launcher flag.",
            execution_time_ms=(time.time() - start_time) * 1000,
            is_sandboxed=False,
        )

    # Prepare command to execute
    if language == "python":
        inner_cmd = ["/usr/bin/python3", "-c", code]
    elif language == "bash":
        inner_cmd = ["/bin/bash", "-c", code]
    else:
        raise ValueError(f"Unsupported language: {language}")

    # Build sandbox invocation command
    cmd = [SANDBOX_BIN, "do"]
    if allow_write:
        cmd.append("--write")
    if allow_egress:
        cmd.append("--allow-egress")
    cmd.append("--")
    cmd.extend(inner_cmd)

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_sec,
        )
        elapsed_ms = (time.time() - start_time) * 1000
        return ExecutionResponse(
            success=(proc.returncode == 0),
            exit_code=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            execution_time_ms=elapsed_ms,
            is_sandboxed=True,
        )
    except subprocess.TimeoutExpired as e:
        elapsed_ms = (time.time() - start_time) * 1000
        return ExecutionResponse(
            success=False,
            exit_code=124,
            stdout=e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or ""),
            stderr=f"Execution timed out after {timeout_sec} seconds.",
            execution_time_ms=elapsed_ms,
            is_sandboxed=True,
        )
    except Exception as e:
        elapsed_ms = (time.time() - start_time) * 1000
        return ExecutionResponse(
            success=False,
            exit_code=1,
            stdout="",
            stderr=f"Execution failed: {str(e)}",
            execution_time_ms=elapsed_ms,
            is_sandboxed=True,
        )


@app.get("/")
def health_check():
    return {
        "status": "healthy",
        "sandbox_available": bool(SANDBOX_BIN),
        "sandbox_path": SANDBOX_BIN or "Not Found",
    }


@app.post("/run", response_model=ExecutionResponse)
def run_code(req: ExecutionRequest):
    return execute_in_sandbox(
        language=req.language,
        code=req.code,
        allow_write=req.allow_write,
        allow_egress=req.allow_egress,
        timeout_sec=req.timeout_sec,
    )


@app.post("/test/env-isolation", response_model=ExecutionResponse)
def test_env_isolation():
    """Verify that host environment variables cannot be accessed inside the sandbox."""
    # Set a dummy secret in the host process environment
    os.environ["HOST_SUPER_SECRET"] = "secret-token-do-not-leak"
    
    # Attempt to print it from inside the sandbox
    python_probe = "import os; val = os.getenv('HOST_SUPER_SECRET', '<NOT_FOUND>'); print(f'HOST_SUPER_SECRET={val}')"
    return execute_in_sandbox(language="python", code=python_probe)


@app.post("/test/metadata-isolation", response_model=ExecutionResponse)
def test_metadata_isolation():
    """Verify that the GCP Metadata Server (169.254.169.254) cannot be reached from the sandbox."""
    bash_probe = "curl -s --connect-timeout 2 -H 'Metadata-Flavor: Google' http://169.254.169.254/computeMetadata/v1/instance/service-accounts/default/token || echo 'METADATA_ACCESS_BLOCKED'"
    return execute_in_sandbox(language="bash", code=bash_probe, allow_egress=False)


@app.post("/test/fs-isolation", response_model=ExecutionResponse)
def test_fs_isolation():
    """Verify that the root filesystem is read-only when --write is NOT specified."""
    bash_probe = "echo 'malicious write' > /test_probe.txt"
    return execute_in_sandbox(language="bash", code=bash_probe, allow_write=False)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
