from __future__ import annotations

from pathlib import Path

import torch
from fastapi import FastAPI, HTTPException

from streamlit_ui.heritage_data import load_heritage_metadata


PROJECT_ROOT = Path(__file__).resolve().parent.parent
app = FastAPI(title="Tái sinh Di sản Số API", version="0.1.0")


def heritage_items() -> list[dict]:
    return load_heritage_metadata(PROJECT_ROOT)


@app.get("/health")
def health() -> dict:
    device = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu"
    return {"status": "ok", "cuda": torch.cuda.is_available(), "device": device}


@app.get("/heritage")
def list_heritage() -> list[dict]:
    return heritage_items()


@app.get("/heritage/{heritage_id}")
def get_heritage(heritage_id: str) -> dict:
    item = next((item for item in heritage_items() if item["heritage_id"] == heritage_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy hiện vật.")
    return item


@app.post("/generate", status_code=501)
def generate_designs() -> dict:
    return {"detail": "Endpoint sẽ được nối pipeline ở Phase 4."}
