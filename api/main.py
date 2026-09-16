from __future__ import annotations

from pathlib import Path
import json

import torch
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from streamlit_ui.heritage_data import load_heritage_metadata


PROJECT_ROOT = Path(__file__).resolve().parent.parent
app = FastAPI(title="Tái sinh Di sản Số API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500", "http://localhost:5500"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def heritage_items() -> list[dict]:
    return load_heritage_metadata(PROJECT_ROOT)


def ui_items() -> list[dict]:
    presentation = json.loads((PROJECT_ROOT / "data" / "heritage" / "items.json").read_text(encoding="utf-8"))
    presentation_by_id = {item["id"]: item for item in presentation}
    result = []
    for item in heritage_items():
        legacy = presentation_by_id.get(item["heritage_id"], {})
        result.append({
            "id": item["heritage_id"],
            "name": item["name"],
            "dynasty": legacy.get("era", "Di sản Bát Tràng"),
            "glaze": item["conditioning_mode"],
            "category": ["all"],
            "categoryLabel": legacy.get("category", "Hiện vật Bát Tràng"),
            "image": f"http://127.0.0.1:8000/media/heritage/{item['heritage_id']}",
            "colors": [],
            "colorNames": [],
            "desc": item["team_description"],
            "licenseNote": item["license_note"],
            "variantImageBase": f"./assets/images/variants/{item['heritage_id']}_V",
        })
    return result


@app.get("/health")
def health() -> dict:
    device = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu"
    return {"status": "ok", "cuda": torch.cuda.is_available(), "device": device}


@app.get("/heritage")
def list_heritage() -> list[dict]:
    return ui_items()


@app.get("/heritage/{heritage_id}")
def get_heritage(heritage_id: str) -> dict:
    item = next((item for item in ui_items() if item["id"] == heritage_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy hiện vật.")
    return item


@app.get("/media/heritage/{heritage_id}")
def heritage_image(heritage_id: str) -> FileResponse:
    item = next((item for item in heritage_items() if item["heritage_id"] == heritage_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy ảnh hiện vật.")
    path = PROJECT_ROOT / item["image_path"]
    return FileResponse(path)


@app.post("/generate", status_code=501)
def generate_designs() -> dict:
    return {"detail": "Endpoint sẽ được nối pipeline ở Phase 4."}
