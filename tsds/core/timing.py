# -*- coding: utf-8 -*-
"""Đo thời gian từng giai đoạn của một lượt sinh.

Dùng đồng hồ đơn điệu `time.perf_counter()` (không nhảy khi hệ điều hành chỉnh giờ), khác `time.time()`.
Định nghĩa từng con số ghi vào Passport và manifest nằm ở docs/DO_THOI_GIAN.md.
"""
from __future__ import annotations

import time
from contextlib import contextmanager

SCHEMA = "timing/1.0"


@contextmanager
def timed(store: dict, key: str):
    """Đo khối lệnh bên trong và CỘNG DỒN vào store[key] (giây).

    Cộng dồn để một giai đoạn chạy nhiều lần (ví dụ sinh lại hoa văn) ra tổng thời gian.
    Khối lệnh ném ngoại lệ vẫn ghi thời gian đã tốn rồi mới ném tiếp."""
    t0 = time.perf_counter()
    try:
        yield
    finally:
        store[key] = store.get(key, 0.0) + (time.perf_counter() - t0)


def rounded(store: dict, ndigits: int = 2) -> dict:
    """Bản sao làm tròn để ghi file. Giữ nguyên store gốc."""
    return {k: round(v, ndigits) for k, v in store.items()}
