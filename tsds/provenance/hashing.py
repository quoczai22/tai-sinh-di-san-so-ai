# -*- coding: utf-8 -*-
"""Băm SHA-256 ĐẦY ĐỦ (64 ký tự) cho mọi tệp trong chuỗi truy vết.

16 ký tự hex (64 bit) đủ để phát hiện sai khác ngẫu nhiên nhưng không phải chuẩn chứng
minh toàn vẹn, nên Passport luôn lưu đủ 64 ký tự.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path | str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_json(obj) -> str:
    """JSON chuẩn hoá (sắp khoá, không khoảng trắng thừa) để băm ổn định."""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(obj) -> str:
    return sha256_bytes(canonical_json(obj).encode("utf-8"))
