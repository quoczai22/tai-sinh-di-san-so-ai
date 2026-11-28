# -*- coding: utf-8 -*-
"""Cổng kiểm tra ảnh đầu vào của pipeline (mô tả đầy đủ ở docs/CONG_ANH_DAU_VAO.md).

Ảnh nạp vào ControlNet (ảnh hiện vật hoặc phần tử trong kho) phải thuộc miền gốm và hoa văn. Cổng nhúng ảnh bằng CLIP rồi chấm
theo nguyên mẫu (P): s_proto = trung bình k độ giống cao nhất (cosine ảnh với ảnh) với ảnh tham chiếu trong kho.
Có MỘT ngưỡng t: điểm >= t là pass, điểm < t là block (không có vùng warn). Ngưỡng đặt trong config/input_gate.json,
đo bằng scripts/eval/run_input_gate_eval.py. (Cách chấm bằng từ khóa T đã thử rồi bỏ, xem docs/CONG_ANH_DAU_VAO.md.)

Cổng chạy CPU (không tranh VRAM với bộ sinh ảnh). Cổng lỗi thì CHẶN (InputRejected), vì ảnh do nhóm kiểm soát.
Mỗi lần block hoặc lỗi ghi một dòng vào outputs/audit/input_gate.jsonl (không ghi IP, không ghi nội dung ảnh).
Tầng quality không được import api, nên cổng tự ghi log của mình.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image

from tsds.core.paths import CONFIG_DIR, DATA_DIR, HERITAGE_DIR, OUTPUTS_DIR, ROOT

CONFIG_PATH = CONFIG_DIR / "input_gate.json"
CLIP_ID = "openai/clip-vit-base-patch32"
PREP_VERSION = 1                         # tăng khi đổi cách chuẩn hóa ảnh (prepare_image) để bỏ đệm nguyên mẫu cũ
N_REF_PER_VASE = 10                     # số phần tử lấy làm nguyên mẫu cho mỗi bình (lấy đều theo mã phần tử)


class InputRejected(Exception):
    """Ảnh đầu vào bị cổng chặn (hoặc cổng không chạy được). Cố ý KHÔNG kế thừa ValueError hay OSError,
    vì generate_design_set bắt hai lớp đó để quay về ảnh mặc định, và như vậy sẽ nuốt mất việc chặn."""

    def __init__(self, message: str, results: list[dict] | None = None):
        super().__init__(message)
        self.results = results or []


# ---------------------------------------------------------------- cấu hình --
def load_config(path: Path | None = None) -> dict:
    return json.loads(Path(path or CONFIG_PATH).read_text(encoding="utf-8"))


# ------------------------------------------------------------ chuẩn hóa ảnh --
def prepare_image(img: Image.Image) -> Image.Image:
    """RGBA đặt lên nền trắng, rồi đệm trắng thành hình vuông để CLIP (cắt giữa) không mất phần mép."""
    if img.mode in ("RGBA", "LA") or "transparency" in img.info:     # gồm cả ảnh bảng màu (P) có màu trong suốt
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg
    img = img.convert("RGB")
    side = max(img.size)
    canvas = Image.new("RGB", (side, side), (255, 255, 255))
    canvas.paste(img, ((side - img.width) // 2, (side - img.height) // 2))
    return canvas


# --------------------------------------------------------------------- CLIP --
@lru_cache(maxsize=1)
def _clip():
    import torch                                            # noqa: PLC0415
    from transformers import CLIPModel, CLIPProcessor        # noqa: PLC0415
    torch.set_grad_enabled(False)
    return CLIPModel.from_pretrained(CLIP_ID).eval(), CLIPProcessor.from_pretrained(CLIP_ID)


def _norm(x: np.ndarray) -> np.ndarray:
    return x / np.linalg.norm(x, axis=-1, keepdims=True)


def embed_images(images: list[Image.Image]) -> np.ndarray:
    """Embedding đã chuẩn hóa, kích thước (n, 512). Ảnh được chuẩn hóa bằng prepare_image."""
    import torch                                            # noqa: PLC0415
    m, p = _clip()
    out = []
    with torch.no_grad():
        for im in images:
            x = p(images=prepare_image(im), return_tensors="pt")
            out.append(m.visual_projection(m.vision_model(**x).pooler_output)[0].numpy())
    return _norm(np.stack(out).astype(np.float32))


# --------------------------------------------------------------- nguyên mẫu --
def reference_files() -> list[tuple[Path, str]]:
    """Ảnh tham chiếu của kho: (đường dẫn, mã bình). Ảnh hiện vật + tối đa N_REF_PER_VASE phần tử mỗi bình (lấy đều)."""
    refs: list[tuple[Path, str]] = []
    crops = json.loads((HERITAGE_DIR / "lr3d_crops.json").read_text(encoding="utf-8"))
    for hid, info in sorted(crops.items()):
        f = HERITAGE_DIR / f"{hid}.png"
        if f.is_file():
            refs.append((f, info["object_id"]))
    index = json.loads((DATA_DIR / "elements" / "index.json").read_text(encoding="utf-8"))
    by_obj: dict[str, list[str]] = {}
    for r in index:
        if (ROOT / r["file"]).is_file():
            by_obj.setdefault(r["object_id"], []).append(r["file"])
    for obj, files in sorted(by_obj.items()):
        files = sorted(files)
        pick = np.linspace(0, len(files) - 1, min(N_REF_PER_VASE, len(files))).round().astype(int)
        refs += [(ROOT / files[i], obj) for i in sorted(set(pick))]
    return refs


def load_prototypes() -> tuple[np.ndarray, list[str]]:
    """(embedding nguyên mẫu, mã bình của từng nguyên mẫu). Lưu đệm trên đĩa theo danh sách và kích thước tệp,
    vì nhúng khoảng 90 ảnh trên CPU mất cỡ chục giây, không nên làm lại mỗi lượt sinh."""
    refs = reference_files()
    # Khóa đệm gồm model CLIP và PREP_VERSION (tăng số này khi đổi prepare_image) để đệm cũ không bị dùng nhầm
    key = hashlib.sha256(json.dumps([CLIP_ID, PREP_VERSION, [(p.as_posix(), p.stat().st_size, o) for p, o in refs]])
                         .encode()).hexdigest()[:16]
    cache = OUTPUTS_DIR / "input_gate" / f"prototypes_{key}.npz"
    if cache.exists():
        try:
            z = np.load(cache, allow_pickle=False)
            return z["emb"], [str(o) for o in z["obj"]]
        except Exception:                                   # noqa: BLE001  tệp đệm hỏng thì tính lại, không chặn oan
            pass
    emb = embed_images([Image.open(p) for p, _ in refs])
    objs = [o for _, o in refs]
    cache.parent.mkdir(parents=True, exist_ok=True)
    tmp = cache.with_name(cache.name + ".tmp.npz")          # ghi ra tệp tạm rồi đổi tên, tiến trình chết giữa chừng không để lại tệp hỏng
    np.savez(tmp, emb=emb, obj=np.array(objs))
    os.replace(tmp, cache)
    return emb, objs


# ----------------------------------------------------------- chấm và quyết định --
def score_p(emb: np.ndarray, protos: np.ndarray, k: int = 3, exclude: np.ndarray | None = None) -> np.ndarray:
    """s_proto cho từng ảnh: trung bình k độ giống cao nhất với nguyên mẫu.
    exclude: mảng bool (n_ảnh, n_nguyên_mẫu), True là bỏ nguyên mẫu đó (dùng khi đo kiểu bỏ một bình ra)."""
    sims = emb @ protos.T
    if exclude is not None:
        sims = np.where(exclude, -np.inf, sims)
    top = -np.sort(-sims, axis=1)[:, :k]
    # Số nguyên mẫu còn lại ít hơn k thì chỉ lấy trung bình các nguyên mẫu còn lại; không còn nguyên mẫu nào thì
    # trả -1 (độ giống thấp nhất có thể), tức là không có bằng chứng ảnh thuộc miền.
    ok = np.isfinite(top)
    n = ok.sum(axis=1)
    return np.where(n > 0, np.where(ok, top, 0.0).sum(axis=1) / np.maximum(n, 1), -1.0)


def verdict(score: float, t: float) -> str:
    """score cao hơn hoặc bằng ngưỡng t thì pass, thấp hơn thì block."""
    return "pass" if score >= t else "block"


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Khoảng tin cậy Wilson 95% cho tỉ lệ k/n."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


# -------------------------------------------------------------------- runtime --
def _log(event: dict, log_dir: Path | None = None) -> None:
    """Ghi một dòng vào outputs/audit/input_gate.jsonl. Không để lỗi ghi file làm hỏng việc chặn."""
    try:
        base = Path(os.getenv("DH_OUTPUT_DIR", "").strip() or OUTPUTS_DIR)
        base = base if base.is_absolute() else ROOT / base
        d = log_dir or base / "audit"
        d.mkdir(parents=True, exist_ok=True)
        with open(d / "input_gate.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"), **event},
                               ensure_ascii=False) + "\n")
    except OSError:
        pass


def gate_block(results: list[dict], cfg: dict | None = None) -> dict:
    """Khối ghi vào manifest và Passport (generation.input_gate): kết quả từng ảnh của lượt chạy.
    Ảnh block đã làm check_inputs ném lỗi từ trước, nên ở đây phán quyết chung luôn là pass."""
    cfg = cfg or load_config()
    return {"schema": "input-gate/1.0", "config_version": cfg.get("version"), "calibrated": bool(cfg.get("calibrated")),
            "method": "prototype", "verdict": "pass", "images": results}


def check_inputs(images: list[tuple[str, Path]], context: dict | None = None, cfg: dict | None = None,
                 log_dir: Path | None = None) -> list[dict]:
    """Kiểm các ảnh nạp vào pipeline. images: danh sách (nhãn nguồn, đường dẫn), ảnh trùng đường dẫn chỉ kiểm một lần.

    Trả về danh sách kết quả từng ảnh (khóa: label, path, sha256, s_proto, verdict). Có ảnh block hoặc cổng không chạy được thì ném InputRejected (sau khi ghi log)."""
    context = context or {}
    try:
        cfg = cfg or load_config()
        seen: dict[Path, str] = {}
        for label, path in images:
            seen.setdefault(Path(path), label)
        paths = list(seen)
        emb = embed_images([Image.open(p) for p in paths])
        protos, _ = load_prototypes()
        sp = score_p(emb, protos, k=cfg["P"]["k"])
        results = []
        for i, p in enumerate(paths):
            results.append({
                "label": seen[p], "path": p.relative_to(ROOT).as_posix() if ROOT in p.parents else p.as_posix(),
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                "s_proto": round(float(sp[i]), 4), "verdict": verdict(float(sp[i]), cfg["P"]["t"])})
    except Exception as exc:                                    # noqa: BLE001  cổng lỗi thì chặn
        _log({"event": "input_gate_error", "error_type": type(exc).__name__, **context}, log_dir)
        raise InputRejected(f"Cổng kiểm tra ảnh đầu vào không chạy được ({type(exc).__name__}).") from exc
    version = cfg.get("version")
    for r in results:
        if r["verdict"] == "block":
            _log({"event": "input_blocked", "config_version": version, **context, **r}, log_dir)
    if any(r["verdict"] == "block" for r in results):
        raise InputRejected("Ảnh đầu vào không đạt kiểm tra.", results)
    return results
