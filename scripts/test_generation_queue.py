"""Verify that one GPU job runs at a time and later users wait in order."""
from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import types

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["DH_OUTPUT_DIR"] = tempfile.mkdtemp(prefix="dh_queue_")

started = threading.Event()
release = threading.Event()
calls: list[str] = []


def fake_generate(heritage_id: str, progress, seed: int) -> list[dict]:
    calls.append(heritage_id)
    started.set()
    if heritage_id == "LR3D_33":
        assert release.wait(10)
    progress(90, "Hoàn thiện")
    return [{"status": "completed", "run_id": "R20261121T000000-TEST",
             "design_path": "V1_aodai.png"}]


fake_module = types.ModuleType("generation.streamlit_runner")
fake_module.SEED = 42
fake_module.generate_design_set = fake_generate
sys.modules["generation.streamlit_runner"] = fake_module

from api import main  # noqa: E402

main.append_audit_event = lambda *_args, **_kwargs: True


def wait_for(job_id: str) -> dict:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        job = main.generate_status(job_id)
        if job["status"] in {"completed", "failed"}:
            return job
        time.sleep(0.02)
    raise AssertionError(f"Job {job_id} did not finish")


def test_queue() -> None:
    from api.main import GenerateRequest

    first = main.generate_designs(GenerateRequest(heritage_id="LR3D_33", seed=1))
    assert started.wait(5)
    queued = [main.generate_designs(GenerateRequest(heritage_id="LR3D_61", seed=seed))
              for seed in (2, 3)]
    assert [job["queue_position"] for job in queued] == [1, 2]
    assert calls == ["LR3D_33"]
    try:
        main.generate_designs(GenerateRequest(heritage_id="LR3D_61", seed=4))
    except HTTPException as error:
        assert error.status_code == 429
    else:
        raise AssertionError("Full queue must reject the next request")
    release.set()
    assert wait_for(first["job_id"])["status"] == "completed"
    for job in queued:
        assert wait_for(job["job_id"])["status"] == "completed"
    assert calls == ["LR3D_33", "LR3D_61", "LR3D_61"]
    main._jobs.clear()
    assert main.generate_status(first["job_id"])["status"] == "completed"
    print("generation queue: 3 sequential jobs, 1 full-queue rejection, persistent result passed")


if __name__ == "__main__":
    try:
        test_queue()
    finally:
        release.set()
