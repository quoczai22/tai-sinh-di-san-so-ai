from __future__ import annotations

import json
from pathlib import Path


REQUIRED_FIELDS = {
    "heritage_id",
    "name",
    "image_path",
    "license",
    "license_note",
    "conditioning_mode",
}


def load_heritage_metadata(project_root: Path, include_retired: bool = False) -> list[dict]:
    """Đọc và kiểm tra dữ liệu hiện vật do nhóm cung cấp.

    Schema 2.x thêm trường `status`. Mặc định chỉ trả hiện vật `active`: hiện vật
    `retired` (ví dụ ảnh dưới 512 px) không được đưa vào pipeline sinh ảnh mới,
    nhưng vẫn nằm trong metadata để Design Passport cũ tra được nguồn.
    """
    metadata_path = project_root / "data" / "heritage" / "metadata.json"
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    raw_items = payload.get("items")
    if not isinstance(raw_items, dict) or not raw_items:
        raise ValueError("metadata.json phải có trường items không rỗng.")

    items: list[dict] = []
    for key, item in raw_items.items():
        if not isinstance(item, dict):
            raise ValueError(f"Hiện vật {key} không đúng định dạng object.")
        missing = REQUIRED_FIELDS.difference(item)
        if missing:
            raise ValueError(f"Hiện vật {key} thiếu trường: {', '.join(sorted(missing))}.")
        if item["heritage_id"] != key:
            raise ValueError(f"Khóa items và heritage_id không khớp cho {key}.")
        if not (project_root / item["image_path"]).is_file():
            raise FileNotFoundError(f"Không tìm thấy ảnh hiện vật: {item['image_path']}")
        if item.get("status", "active") != "active" and not include_retired:
            continue
        items.append(item)
    if not items:
        raise ValueError("Không có hiện vật nào ở trạng thái active.")

    return items
