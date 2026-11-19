"""Chỉ số M5: đo độ liền mạch (seam) của một ô hoa văn lát.

Ý tưởng: khi lát ảnh, cột cuối nằm sát cột đầu (và hàng cuối sát hàng đầu).
Nếu ảnh liền mạch thì độ lệch giữa hai cột đó cũng nhỏ như độ lệch giữa hai
cột kề nhau bên trong ảnh.

    M5 = độ lệch tại đường nối / độ lệch trung bình giữa các cặp kề nhau bên trong

1,0 là liền hoàn toàn. Ngưỡng đề xuất 1,3 trở xuống (docs/HUONG_CAI_TIEN_V2.md, mục 8.1).
Ảnh có đường nối rõ sẽ cho giá trị lớn hơn nhiều (hàng chục).

Độ lệch tính trên ba kênh RGB nên gồm cả lệch màu lẫn lệch sáng.
Chạy thử trên ảnh thật:  uv run python -m evaluation.seam anh1.png anh2.png
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

NGUONG_M5 = 1.3   # M5 <= ngưỡng này thì coi là liền mạch
_EPS = 1e-6       # độ lệch nhỏ hơn mức này coi như bằng 0


def _doc_anh(anh) -> np.ndarray:
    """Đọc đường dẫn, ảnh PIL hoặc mảng numpy thành mảng float32 cao x rộng x 3 kênh."""
    if isinstance(anh, (str, Path)):
        anh = Image.open(anh)
    if isinstance(anh, Image.Image):
        return np.asarray(anh.convert("RGB"), dtype=np.float32)
    a = np.asarray(anh, dtype=np.float32)
    if a.ndim == 2:                       # ảnh xám: nhân ra ba kênh
        a = np.repeat(a[..., None], 3, axis=2)
    elif a.ndim == 3 and a.shape[2] >= 3:
        a = a[..., :3]                    # bỏ kênh alpha nếu có
    else:
        raise ValueError(f"Hình dạng ảnh không hợp lệ: {a.shape}")
    return a


def _ti_so(lech_noi: float, lech_trong: float) -> float:
    """Tỉ số độ lệch ở đường nối so với bên trong. Ảnh phẳng hoàn toàn cho 1,0."""
    if lech_trong <= _EPS:
        return 1.0 if lech_noi <= _EPS else float("inf")
    return lech_noi / lech_trong


def seam_score(anh) -> dict:
    """Tính M5 cho một ô hoa văn.

    Trả về dict:
      ratio_x: tỉ số ở đường nối trái-phải
      ratio_y: tỉ số ở đường nối trên-dưới
      m5:      giá trị lớn hơn trong hai tỉ số (lấy trường hợp xấu nhất)
      ok:      True nếu m5 <= NGUONG_M5
    """
    a = _doc_anh(anh)
    if a.shape[0] < 3 or a.shape[1] < 3:
        raise ValueError(f"Ảnh quá nhỏ để đo (cần ít nhất 3x3 pixel): {a.shape[:2]}")

    # Trái-phải: cột đầu so với cột cuối, đối chiếu với mọi cặp cột kề nhau.
    rx = _ti_so(np.abs(a[:, 0] - a[:, -1]).mean(), np.abs(np.diff(a, axis=1)).mean())
    # Trên-dưới: hàng đầu so với hàng cuối, đối chiếu với mọi cặp hàng kề nhau.
    ry = _ti_so(np.abs(a[0] - a[-1]).mean(), np.abs(np.diff(a, axis=0)).mean())

    m5 = max(rx, ry)
    return {"ratio_x": rx, "ratio_y": ry, "m5": m5, "ok": m5 <= NGUONG_M5}


def main(argv: list[str]) -> int:
    """In M5 cho từng ảnh trong danh sách đường dẫn."""
    if not argv:
        print("Cách dùng: python -m evaluation.seam <anh1> [anh2 ...]")
        return 1
    for p in argv:
        r = seam_score(p)
        print(f"{'ĐẠT ' if r['ok'] else 'LỖI '} M5={r['m5']:.2f} "
              f"(x={r['ratio_x']:.2f}, y={r['ratio_y']:.2f})  {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
