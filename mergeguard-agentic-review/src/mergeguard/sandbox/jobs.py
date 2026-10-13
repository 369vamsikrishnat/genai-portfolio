from __future__ import annotations

import json
import os
import shutil
import signal
import stat
import subprocess
import tempfile
import time
import zipfile
from io import BytesIO
from pathlib import Path, PurePosixPath
from uuid import UUID

from mergeguard.tools.sandbox_client import TestResult


MAX_ARCHIVE_BYTES = 50 * 1024 * 1024
MAX_EXTRACTED_BYTES = 200 * 1024 * 1024
MAX_ARCHIVE_FILES = 10_000
TEST_TIMEOUT_SECONDS = 180


def extract_source_archive(archive: bytes, destination: Path) -> None:
    if len(archive) > MAX_ARCHIVE_BYTES:
        raise ValueError("Source archive exceeds the download limit.")

    destination.mkdir(parents=True, exist_ok=False)
    root = destination.resolve()
    with zipfile.ZipFile(BytesIO(archive)) as source:
        entries = source.infolist()
        if len(entries) > MAX_ARCHIVE_FILES:
            raise ValueError("Source archive contains too many files.")
        expanded_size = sum(entry.file_size for entry in entries)
        if expanded_size > MAX_EXTRACTED_BYTES:
            raise ValueError("Source archive expands beyond the extraction limit.")

        prefix = entries[0].filename.split("/", 1)[0] if entries else ""
        for entry in entries:
            parts = PurePosixPath(entry.filename).parts
            if not parts or PurePosixPath(entry.filename).is_absolute() or ".." in parts:
                raise ValueError("Source archive contains an unsafe path.")
            if stat.S_ISLNK(entry.external_attr >> 16):
                raise ValueError("Source archive contains a symbolic link.")

            relative_parts = parts[1:] if parts[0] == prefix else parts
            if not relative_parts:
                continue
            target = destination.joinpath(*relative_parts)
            if not target.resolve().is_relative_to(root):
                raise ValueError("Source archive contains an unsafe path.")
            if entry.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with source.open(entry) as input_file, target.open("wb") as output_file:
                shutil.copyfileobj(input_file, output_file)


def submit_sandbox_job(job_id: str, timeout: float = 210) -> TestResult:
    job_id = str(UUID(job_id))
    request_dir = Path(os.getenv("SANDBOX_REQUEST_DIR", "/sandbox/requests"))
    result_dir = Path(os.getenv("SANDBOX_RESULT_DIR", "/sandbox/results"))
    request_path = request_dir / f"{job_id}.json"
    result_path = result_dir / f"{job_id}.json"
    temporary_request = request_path.with_suffix(".tmp")
    temporary_request.write_text(json.dumps({"job_id": job_id}), encoding="utf-8")
    temporary_request.replace(request_path)

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if result_path.exists():
            result = TestResult.model_validate_json(result_path.read_text(encoding="utf-8"))
            result_path.unlink()
            return result
        time.sleep(0.2)

    request_path.unlink(missing_ok=True)
    return TestResult(
        status="error",
        summary="Isolated test runner did not return a result before the deadline.",
        coverage_delta=None,
        network_disabled=True,
    )


def run_sandbox_worker() -> None:
    request_dir = Path(os.getenv("SANDBOX_REQUEST_DIR", "/sandbox/requests"))
    workspace_dir = Path(os.getenv("SANDBOX_WORKSPACE_DIR", "/sandbox/workspaces"))
    result_dir = Path(os.getenv("SANDBOX_RESULT_DIR", "/sandbox/results"))
    request_dir.mkdir(parents=True, exist_ok=True)
    workspace_dir.mkdir(parents=True, exist_ok=True)
    result_dir.mkdir(parents=True, exist_ok=True)

    while True:
        for request_path in request_dir.glob("*.json"):
            try:
                job_id = str(UUID(request_path.stem))
                request_path.unlink(missing_ok=True)
                result = _run_workspace_tests(workspace_dir / job_id)
            except Exception as error:
                result = TestResult(
                    status="error",
                    summary=f"Sandbox test runner error: {error}",
                    coverage_delta=None,
                    network_disabled=True,
                )
                job_id = request_path.stem

            result_path = result_dir / f"{job_id}.json"
            temporary_result = result_path.with_suffix(".tmp")
            temporary_result.write_text(result.model_dump_json(), encoding="utf-8")
            temporary_result.replace(result_path)
        time.sleep(0.2)


def _run_workspace_tests(workspace: Path) -> TestResult:
    if not workspace.is_dir():
        return TestResult(
            status="error",
            summary="Sandbox workspace does not exist.",
            coverage_delta=None,
            network_disabled=True,
        )

    with tempfile.TemporaryDirectory(prefix="mergeguard-") as scratch_dir:
        os.chmod(scratch_dir, 0o777)
        output_path = Path(scratch_dir) / "pytest-output.txt"
        environment = {
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "HOME": scratch_dir,
            "TMPDIR": scratch_dir,
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        with output_path.open("w+b") as output_file:
            process = subprocess.Popen(
                ["python", "-m", "pytest", "-p", "no:cacheprovider", "-q"],
                cwd=workspace,
                env=environment,
                stdout=output_file,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                user=10001,
                group=10001,
                extra_groups=[],
            )
            try:
                return_code = process.wait(timeout=TEST_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                return TestResult(
                    status="error",
                    summary="Isolated test execution timed out.",
                    coverage_delta=None,
                    network_disabled=True,
                )

            output_file.seek(0, os.SEEK_END)
            output_file.seek(max(0, output_file.tell() - 20 * 1024))
            output_tail = output_file.read().decode("utf-8", errors="replace").strip()

    if return_code == 0:
        status = "passed"
        summary = output_tail or "Tests passed."
    elif return_code == 1 and ("ModuleNotFoundError" in output_tail or "ImportError" in output_tail):
        status = "error"
        summary = "Dependencies missing in the no-network sandbox; tests could not run."
    elif return_code == 1:
        status = "failed"
        summary = output_tail or "Tests failed."
    else:
        status = "error"
        summary = output_tail or f"Tests could not run (pytest exited with code {return_code})."

    return TestResult(
        status=status,
        summary=summary[-500:],
        coverage_delta=None,
        network_disabled=True,
    )


__all__ = ["extract_source_archive", "run_sandbox_worker", "submit_sandbox_job"]