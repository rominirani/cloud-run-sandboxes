import os
import shutil
import subprocess
import tempfile
import time
import uuid
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(
    title="Cloud Run Sandboxes Autograder",
    description="Automated, secure code judge evaluating untrusted student submissions inside isolated sandboxes",
    version="1.0.0"
)

SANDBOX_BIN = "/usr/local/gcp/bin/sandbox" if os.path.exists("/usr/local/gcp/bin/sandbox") else shutil.which("sandbox")
TEST_SUITE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_suite"))

# Simulate a sensitive platform secret on the host container
os.environ["AUTOGRADER_SECRET_KEY"] = "super-secret-exam-grading-token-12345"


class SubmissionRequest(BaseModel):
    student_id: str = Field(..., example="student_42")
    problem_id: str = Field(default="two_sum", example="two_sum")
    code: str = Field(..., description="Python source code containing solution")
    timeout_sec: int = Field(default=5, ge=1, le=15, description="Max allowed execution duration")


class GradingResponse(BaseModel):
    submission_id: str
    student_id: str
    problem_id: str
    verdict: str
    execution_time_ms: float
    total_tests: int
    passed_tests: int
    failed_tests: int
    details: list
    stdout: str
    stderr: str
    sandbox_used: bool


@app.get("/")
def health():
    return {
        "status": "online",
        "sandbox_present": bool(SANDBOX_BIN),
        "test_suite_path": TEST_SUITE_DIR,
    }


@app.post("/grade", response_model=GradingResponse)
def grade_submission(submission: SubmissionRequest):
    submission_id = str(uuid.uuid4())[:8]
    start_time = time.time()

    # Create temporary host directory for this specific submission
    work_dir = tempfile.mkdtemp(prefix=f"sub_{submission_id}_")
    student_file = os.path.join(work_dir, "solution.py")

    try:
        with open(student_file, "w") as f:
            f.write(submission.code)

        if not SANDBOX_BIN:
            raise HTTPException(
                status_code=500,
                detail="Cloud Run Sandbox binary (/usr/local/gcp/bin/sandbox) not found. Deploy with --sandbox-launcher."
            )

        # Build sandbox command with two read-only bind mounts:
        # 1. /mnt/test_suite: read-only access to runner.py
        # 2. /mnt/student: read-only access to solution.py
        cmd = [
            SANDBOX_BIN, "do",
            "--mount", f"type=bind,source={TEST_SUITE_DIR},destination=/mnt/test_suite,readonly",
            "--mount", f"type=bind,source={work_dir},destination=/mnt/student,readonly",
            "--",
            "/usr/bin/python3", "/mnt/test_suite/runner.py"
        ]

        try:
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=submission.timeout_sec,
            )
            elapsed_ms = (time.time() - start_time) * 1000

            # Parse JSON output from the test runner if possible
            import json
            parsed = None
            for line in proc.stdout.splitlines():
                line = line.strip()
                if line.startswith("{") and line.endswith("}"):
                    try:
                        parsed = json.loads(line)
                        break
                    except json.JSONDecodeError:
                        continue

            if parsed:
                return GradingResponse(
                    submission_id=submission_id,
                    student_id=submission.student_id,
                    problem_id=submission.problem_id,
                    verdict=parsed.get("verdict", "UNKNOWN"),
                    execution_time_ms=elapsed_ms,
                    total_tests=parsed.get("total_tests", 0),
                    passed_tests=parsed.get("passed_tests", 0),
                    failed_tests=parsed.get("failed_tests", 0),
                    details=parsed.get("details", []),
                    stdout=proc.stdout,
                    stderr=proc.stderr,
                    sandbox_used=True,
                )
            else:
                verdict = "ACCEPTED" if proc.returncode == 0 else "RUNTIME_ERROR"
                return GradingResponse(
                    submission_id=submission_id,
                    student_id=submission.student_id,
                    problem_id=submission.problem_id,
                    verdict=verdict,
                    execution_time_ms=elapsed_ms,
                    total_tests=0,
                    passed_tests=0,
                    failed_tests=0,
                    details=[],
                    stdout=proc.stdout,
                    stderr=proc.stderr,
                    sandbox_used=True,
                )

        except subprocess.TimeoutExpired as e:
            elapsed_ms = (time.time() - start_time) * 1000
            return GradingResponse(
                submission_id=submission_id,
                student_id=submission.student_id,
                problem_id=submission.problem_id,
                verdict="TIME_LIMIT_EXCEEDED",
                execution_time_ms=elapsed_ms,
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                details=[{"error": f"Execution exceeded time limit of {submission.timeout_sec}s"}],
                stdout=e.stdout or "",
                stderr=e.stderr or "",
                sandbox_used=True,
            )

    finally:
        # Cleanup host temp directory
        shutil.rmtree(work_dir, ignore_errors=True)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run("autograder:app", host="0.0.0.0", port=port)
