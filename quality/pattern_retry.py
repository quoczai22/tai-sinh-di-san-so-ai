# -*- coding: utf-8 -*-
"""Vòng sinh lại hoa văn khi cổng G2 báo LỖI (bước quay lại `stage1_regenerate` trong config/quality_gate.json).

Cổng G2 đo hoa văn phẳng ngay sau giai đoạn 1: rò dáng vật chứa (VLS) và đường nối khi lát. Chỉ số nào vượt
ngưỡng LỖI thì hoa văn không dùng được (lát ra thấy đường kẻ, hoặc là ảnh nguyên chiếc bình). Trước đây lỗi này chỉ
được ghi nhận ở cuối lượt chạy, thiết kế đó bị ẩn đi và bộ thiếu mẫu. Vòng này sinh lại ngay trong lượt chạy.

Quy trình cho một thiết kế:
  1. Sinh hoa văn với seed ban đầu, đo G2.
  2. G2 không LỖI (PASS hoặc WARN): dùng luôn. Cảnh báo (WARN) không kích hoạt sinh lại, giống vòng polish.
  3. G2 LỖI: đổi seed (seed + 1, seed + 2, ...), giữ nguyên prompt, trọng số ControlNet và bảng màu.
     Tối đa `max_retries` lần sinh lại (mặc định lấy từ `max_retries` trong cấu hình cổng, hiện là 3).
  4. Vẫn lỗi sau mọi lần: trả bản ít lỗi nhất (chỉ số tệ nhất so với ngưỡng LỖI thấp nhất) kèm trạng thái
     "best_of_failed". G2 vẫn báo LỖI nên Passport ghi `qa_failed`, không có gì bị che giấu.
Mọi lần bị loại ghi vào `outputs/qc/pattern_rejects.csv` và lưu ảnh vào `outputs/qc/pattern_rejects/`.

Lỗi ở bước đo G2 (không phải bước sinh) không làm mất ảnh vừa sinh và không sinh lại: ảnh được dùng với trạng thái
"unmeasured" như trước đây khi cổng G2 không đo được, và việc ghi nhật ký bị loại lỗi cũng không làm hỏng vòng này.

Hàm `generate_with_retry` không tự gọi GPU: hàm sinh và hàm đo được truyền vào, nên kiểm thử được bằng bản giả.
"""
from __future__ import annotations

import csv
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
QC_DIR = ROOT / "outputs" / "qc"
REJECT_COLUMNS = ["timestamp", "tag", "attempt", "seed", "failed_metrics", "values", "thresholds", "reason",
                  "next_action", "image"]


def failed_metrics(g2: dict) -> list[str]:
    """Các chỉ số G2 đang ở mức LỖI."""
    return [k for k, r in g2["metrics"].items() if r["status"] == "FAIL"]


def severity(g2: dict) -> float:
    """Mức tệ của một kết quả G2: giá trị tệ nhất của (giá trị / ngưỡng LỖI) trên các chỉ số "càng thấp càng tốt".

    Bằng hoặc hơn 1 nghĩa là có chỉ số vượt ngưỡng LỖI. Dùng để chọn bản ít lỗi nhất khi mọi lần thử đều lỗi.
    Chỉ số không đo được (giá trị rỗng) bị bỏ qua; không còn chỉ số nào thì trả 0."""
    ratios = []
    for r in g2["metrics"].values():
        v, fail = r.get("value"), r.get("fail")
        if v is None or not fail:
            continue
        ratios.append(float(v) / float(fail))
    return max(ratios, default=0.0)


def _log_reject(qc_dir: Path, tag: str, attempt: int, seed: int, image: Image.Image, g2: dict, failed: list[str],
                next_action: str) -> None:
    """Ghi một dòng vào pattern_rejects.csv và lưu ảnh hoa văn bị loại."""
    qc_dir.mkdir(parents=True, exist_ok=True)
    (qc_dir / "pattern_rejects").mkdir(exist_ok=True)
    path = qc_dir / "pattern_rejects" / f"{tag}_a{attempt}_s{seed}.png"
    image.save(path)
    metrics = g2["metrics"]
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"), "tag": tag, "attempt": attempt,
        "seed": seed, "failed_metrics": ";".join(failed),
        "values": ";".join(f"{k}={metrics[k]['value']}" for k in failed),
        "thresholds": ";".join(f"{k}>={metrics[k]['fail']}" for k in failed),
        "reason": "; ".join(f"{metrics[k]['label']} = {metrics[k]['value']} (ngưỡng lỗi {metrics[k]['fail']})"
                            for k in failed),
        "next_action": next_action, "image": path.relative_to(qc_dir).as_posix(),
    }
    csv_path = qc_dir / "pattern_rejects.csv"
    new = not csv_path.exists()
    with open(csv_path, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=REJECT_COLUMNS)
        if new:
            w.writeheader()
        w.writerow(row)


def generate_with_retry(make: Callable[[int], tuple[Image.Image, dict]],
                        evaluate: Callable[[Image.Image], dict], *, seed: int, max_retries: int | None = None,
                        qc_dir: Path | None = None, tag: str = "design",
                        on_retry: Callable[[int, int], None] | None = None) -> dict:
    """Sinh hoa văn, đo G2, sinh lại theo quy tắc ở đầu file.

    make(seed) -> (ảnh hoa văn cuối cùng, dict kết quả gốc của bước sinh). Ảnh đã khớp bảng màu nếu cần, vì G2
        phải đo đúng ảnh sẽ được dùng.
    evaluate(ảnh) -> kết quả `quality.gate.evaluate_pattern`.
    on_retry(lần thứ, seed) được gọi trước mỗi lần sinh lại (để báo tiến độ).

    Trả về dict: image, result (dict gốc của lần được chọn), seed, status, attempts (danh sách từng lần thử), g2.
    status: "passed" (đạt ngay), "retried_seed" (đạt sau khi đổi seed), "best_of_failed" (mọi lần đều LỖI),
            "unmeasured" (ảnh sinh được nhưng bước đo G2 ném ngoại lệ: dùng ảnh đó, không sinh lại, g2 là None).
    Lần thử mà bước sinh ném ngoại lệ được ghi `status: "error"` và bỏ qua; nếu mọi lần đều ngoại lệ thì ném lại ngoại lệ cuối.
    """
    if max_retries is None:
        from quality import gate as QG                              # noqa: PLC0415
        max_retries = int(QG.load_config().get("max_retries", 3))
    qc_dir = Path(qc_dir) if qc_dir else QC_DIR
    total = max_retries + 1
    attempts: list[dict] = []
    kept: list[tuple[float, int, Image.Image, dict, dict]] = []   # (độ tệ, lần thử, ảnh, kết quả gốc, g2) của các lần đo được
    last_error: Exception | None = None
    for n in range(1, total + 1):
        s = seed + n - 1
        if n > 1 and on_retry:
            on_retry(n, s)
        try:
            image, result = make(s)
        except Exception as exc:                                    # noqa: BLE001
            last_error = exc
            attempts.append({"attempt": n, "seed": s, "status": "error", "error": type(exc).__name__})
            continue
        try:
            g2 = evaluate(image)
        except Exception as exc:                                    # noqa: BLE001
            # Không đo được thì không có căn cứ để bỏ ảnh: giữ ảnh, không đốt thêm GPU để sinh lại
            attempts.append({"attempt": n, "seed": s, "status": "unmeasured", "error": type(exc).__name__})
            return {"image": image, "result": result, "seed": s, "status": "unmeasured", "attempts": attempts, "g2": None}
        failed = failed_metrics(g2)
        values = {k: r["value"] for k, r in g2["metrics"].items()}
        attempts.append({"attempt": n, "seed": s, "status": "failed" if failed else "ok", "decision": g2["decision"],
                         "failed_metrics": failed, "values": values})
        if not failed:
            return {"image": image, "result": result, "seed": s, "status": "passed" if n == 1 else "retried_seed",
                    "attempts": attempts, "g2": g2}
        try:
            _log_reject(qc_dir, tag, n, s, image, g2, failed,
                        "sinh lại với seed kế tiếp" if n < total else "dùng bản ít lỗi nhất, G2 vẫn báo LỖI")
        except OSError:                                             # ghi nhật ký lỗi (ổ đĩa, file đang mở) không được làm hỏng việc sinh
            pass
        kept.append((severity(g2), n, image, result, g2))
    if not kept:
        raise last_error if last_error else RuntimeError("không sinh được hoa văn")
    _, n, image, result, g2 = min(kept, key=lambda t: (t[0], t[1]))   # ít lỗi nhất; bằng nhau thì lấy lần sớm hơn
    return {"image": image, "result": result, "seed": seed + n - 1, "status": "best_of_failed",
            "attempts": attempts, "g2": g2}
