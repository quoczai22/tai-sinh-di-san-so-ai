# -*- coding: utf-8 -*-
"""Provenance & Copyright Registry — một nguồn dữ liệu duy nhất cho hiện vật.

`data/heritage/metadata.json` (schema 2.x) là nguồn chuẩn DUY NHẤT. Hai tệp cũ
(`data/metadata.json`, `data/heritage/items.json`) đã được lưu trữ ở
`data/archive/` vì lệch nhau và gán niên hiệu không có nguồn.

Nguyên tắc vận hành mượn từ kiến trúc quy trình mua hàng (APQC):
  * "Phân luồng ngay từ đầu vào": mỗi hiện vật mang một rights_status ngay khi
    tiếp nhận, và trạng thái đó quyết định PHẠM VI sử dụng.
  * "Kiểm soát tại cổng, do hệ thống thực thi": hàm `rights_gate` chặn xuất bản
    công khai khi quyền chưa rõ, thay vì trông vào việc ai đó nhớ kiểm tra.
  * "Giá trị quyết định cấp duyệt, không quyết định luồng": ảnh chưa xác minh
    vẫn được dùng để THỬ NGHIỆM nội bộ, nhưng không được XUẤT BẢN.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from core.paths import ROOT
METADATA = Path("data") / "heritage" / "metadata.json"
SELECTION_CONFIG = Path("config") / "heritage_selection.json"

RIGHTS_STATUS = {
    "unverified": "Chưa xác minh quyền sử dụng",
    "permission_requested": "Đã gửi đề nghị cấp phép, đang chờ phản hồi",
    "permission_granted": "Đã được chủ sở hữu cho phép (xem phạm vi)",
    "open_license": "Giấy phép mở (CC BY, CC BY-SA…)",
    "public_domain": "Phạm vi công cộng / CC0",
    "own_work": "Ảnh do nhóm tự chụp/tự vẽ",
    "permission_denied": "Chủ sở hữu từ chối — không được dùng",
}

ACTIONS = {
    "experiment": "Thử nghiệm nội bộ (sinh ảnh, đo chỉ số)",
    "demo_display": "Hiển thị trong bản trình diễn phi thương mại",
    "publish_public": "Xuất bản công khai thiết kế",
    "commercial_use": "Sử dụng thương mại",
}

# Trường BTC yêu cầu (Đề cải tiến, mục 3) — nhãn tiếng Việt để hiển thị
REQUIRED_PROVENANCE = {
    "name": "Tên hiện vật",
    "source_title": "Nguồn hiện vật",
    "source_url": "URL nguồn",
    "holder": "Tổ chức lưu giữ / đơn vị đăng ảnh",
    "author": "Tác giả hoặc đơn vị cung cấp ảnh",
    "rights_status": "Tình trạng quyền sử dụng",
    "license": "Giấy phép",
    "attribution": "Cách ghi công",
    "collected_on": "Ngày thu thập",
    "data_version": "Phiên bản dữ liệu gốc",
}


@dataclass
class GateResult:
    allowed: bool
    level: str          # ok | warn | block
    reason: str

    def as_dict(self) -> dict:
        return {"allowed": self.allowed, "level": self.level, "reason": self.reason}


def load_registry(root: Path = ROOT) -> dict:
    return json.loads((root / METADATA).read_text(encoding="utf-8"))


def load_selection_config(root: Path = ROOT) -> dict:
    return json.loads((root / SELECTION_CONFIG).read_text(encoding="utf-8"))


def all_items(root: Path = ROOT) -> list[dict]:
    return list(load_registry(root)["items"].values())


def get_item(heritage_id: str, root: Path = ROOT) -> dict | None:
    return load_registry(root)["items"].get(heritage_id)


def item_status(item: dict) -> str:
    return item.get("status", "active")


def _provenance_value(item: dict, field: str):
    if field == "name":
        return item.get("name")
    return (item.get("provenance") or {}).get(field)


def completeness(item: dict) -> dict:
    """Đếm trường hồ sơ nguồn đã điền. Giá trị `unknown_after_search` được tính là
    ĐÃ XỬ LÝ (nhóm đã tra và ghi rõ không xác định được), khác với để trống."""
    prov = item.get("provenance") or {}
    filled, missing, unknown = [], [], []
    for field, label in REQUIRED_PROVENANCE.items():
        value = _provenance_value(item, field)
        if value in (None, "", []):
            missing.append({"field": field, "label": label})
        elif isinstance(value, str) and value.startswith("unknown"):
            unknown.append({"field": field, "label": label, "note": prov.get(f"{field}_note", "")})
            filled.append(field)
        else:
            filled.append(field)
    total = len(REQUIRED_PROVENANCE)
    return {
        "filled": len(filled), "total": total,
        "ratio": round(len(filled) / total, 3),
        "missing": missing, "declared_unknown": unknown,
    }


def rights_gate(item: dict, action: str, root: Path = ROOT) -> GateResult:
    """Cổng kiểm soát quyền sử dụng — do hệ thống thực thi."""
    if action not in ACTIONS:
        raise ValueError(f"Hành động không hợp lệ: {action}")
    prov = item.get("provenance") or {}
    status = prov.get("rights_status", "unverified")
    cfg = load_selection_config(root)["criteria"]["C3_rights"]
    if item_status(item) == "retired" and action != "experiment":
        return GateResult(False, "block", "Hiện vật đã ngừng sử dụng (retired) — chỉ còn giá trị lưu trữ minh chứng.")
    if status in cfg["blocked_statuses"]:
        return GateResult(False, "block", "Chủ sở hữu đã từ chối cấp phép.")
    if action == "experiment":
        return GateResult(True, "ok" if status != "unverified" else "warn",
                          "Thử nghiệm nội bộ được phép; kết quả không được xuất bản khi quyền chưa rõ."
                          if status == "unverified" else "Được phép.")
    if action == "demo_display":
        if status in cfg["publishable_statuses"]:
            return GateResult(True, "ok", "Được phép hiển thị kèm ghi công.")
        return GateResult(True, "warn", "Chỉ hiển thị phi thương mại, kèm nhãn 'chưa xác minh quyền' và ghi nguồn.")
    if action == "publish_public":
        if status in cfg["publishable_statuses"]:
            return GateResult(True, "ok", "Đủ điều kiện xuất bản kèm ghi công.")
        return GateResult(False, "block", f"Không xuất bản công khai khi quyền ở trạng thái '{RIGHTS_STATUS.get(status, status)}'.")
    # commercial_use
    scope = (prov.get("permission") or {}).get("scope", "")
    # Phạm vi cấp phép là danh sách mục đích ("display, publish, commercial_use"...).
    # So theo từ nguyên vẹn: "non-commercial" KHÔNG được hiểu là cho phép thương mại.
    tokens = {t for t in re.split(r"[,;\s]+", (" ".join(scope) if isinstance(scope, list) else str(scope)).lower()) if t}
    if status in ("public_domain", "own_work") or (status == "permission_granted" and tokens & {"commercial", "commercial_use"}):
        return GateResult(True, "ok", "Được phép sử dụng thương mại.")
    if status == "open_license" and "NC" not in (prov.get("license") or ""):
        return GateResult(True, "warn", "Giấy phép mở cho phép thương mại — phải giữ điều kiện ghi công/chia sẻ tương tự.")
    return GateResult(False, "block", "Chưa có căn cứ cho phép sử dụng thương mại.")


def assess_selection(item: dict, root: Path = ROOT) -> dict:
    """Chạy tiêu chí tuyển ảnh C1–C4 trên một hiện vật. Chỉ dùng OpenCV (CPU)."""
    import numpy as np                                     # noqa: PLC0415
    from PIL import Image                                  # noqa: PLC0415
    from generation import controlnet as cn                # noqa: PLC0415

    cfg = load_selection_config(root)["criteria"]
    path = root / item["image_path"]
    with Image.open(path) as im:
        width, height = im.size
    src, alpha = cn.load_reference(item["heritage_id"])
    mask = (alpha > 10) if alpha is not None else (cn.object_mask(src) > 0)
    ys, xs = np.where(mask)
    obj_w, obj_h = int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)
    upscale = round(cn.RESOLUTION / max(obj_w + 16, obj_h + 16), 3)
    prep = cn.prepare(item["heritage_id"], ornament_only=True, trim=True)

    c1 = cfg["C1_resolution"]
    c1_pass = min(width, height) >= c1["min_short_side"] and max(obj_w, obj_h) >= c1["min_object_long_side"]
    c1_level = "pass" if c1_pass else "fail"
    if c1_pass and max(obj_w, obj_h) < c1["warn_object_long_side"]:
        c1_level = "warn"

    c2 = cfg["C2_ornament_density"]
    threshold = int(round(c2["baseline_edge_px"] * c2["ratio"]))
    edge_px = prep["n_edge_px"]

    prov = item.get("provenance") or {}
    c3_missing = [f for f in ("source_url", "holder", "rights_status") if not prov.get(f)]
    status = prov.get("rights_status", "unverified")
    if c3_missing:
        c3_level = "fail"
    elif status in cfg["C3_rights"]["publishable_statuses"]:
        c3_level = "pass"
    else:
        c3_level = "warn"

    holder_type = prov.get("holder_type", "")
    c4_level = "pass" if holder_type in ("museum", "cultural_institution") and prov.get("dating_source") else "warn"

    levels = [c1_level, "pass" if edge_px >= threshold else "fail", c3_level, c4_level]
    overall = "fail" if "fail" in levels[:2] else ("warn" if "warn" in levels or "fail" in levels else "pass")
    return {
        "heritage_id": item["heritage_id"],
        "C1_resolution": {"level": c1_level, "image_size": [width, height],
                          "object_size": [obj_w, obj_h], "letterbox_scale": upscale},
        "C2_ornament_density": {"level": levels[1], "edge_px": edge_px, "threshold": threshold,
                                "ratio_to_baseline": round(edge_px / c2["baseline_edge_px"], 3)},
        "C3_rights": {"level": c3_level, "rights_status": status, "missing": c3_missing},
        "C4_heritage_authenticity": {"level": c4_level, "holder_type": holder_type or None},
        "technical_overall": overall,
    }
