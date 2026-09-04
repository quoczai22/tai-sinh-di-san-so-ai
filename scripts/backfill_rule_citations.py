#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/backfill_rule_citations.py.

Dry-run / Backfill citation metadata (source_note, locator) vào bảng rule_entries trên Supabase.
Quy tắc an toàn:
- Mặc định CHỈ chạy ở chế độ DRY-RUN (không INSERT, không UPDATE, không can thiệp live DB).
- Đối chiếu đúng rule_id = '{heritage_id}:{category}'.
- Thống kê chi tiết: số rule khớp DB, rule không khớp, số dòng có nguy cơ ghi đè.
- Tuyệt đối không ghi credentials/secrets ra log.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

# Đảm bảo import được backend app modules
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from app.supabase_client import get_supabase_client
except ImportError:
    get_supabase_client = None


# Danh sách các di sản bị loại khỏi phạm vi MVP theo quyết định của BA và AI/Data
EXCLUDED_HERITAGE = {"BT003", "BT004"}


def extract_primary_locator(source_note: str) -> str:
    """Trích xuất câu trích nguyên văn đầu tiên nằm trong cặp nháy đơn '...' của source_note."""
    if not source_note:
        return ""
    matches = re.findall(r"'([^']+)'", source_note)
    if matches:
        # Lấy câu trích đầu tiên có độ dài hợp lý (> 5 ký tự)
        for m in matches:
            cleaned = m.strip()
            if len(cleaned) > 5 and not cleaned.startswith("4 loại chỉ dấu"):
                return cleaned
        return matches[0].strip()
    return ""


def load_rule_base_json(json_path: Path) -> tuple[dict[str, dict], dict[str, dict]]:
    """Đọc data/rule_base.json và phân tách thành:
    1. candidates: các rule thuộc 11 di sản trong phạm vi MVP.
    2. excluded: các rule thuộc di sản bị loại (BT003, BT004).
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    candidates: dict[str, dict] = {}
    excluded: dict[str, dict] = {}
    items = data.get("heritage_items", [])

    for item in items:
        hid = item.get("heritage_id")
        source_note = item.get("source_note", "")
        locator = extract_primary_locator(source_note)
        rule_sources = item.get("rule_sources", {})

        all_categories = (
            item.get("preserve", [])
            + item.get("modifiable", [])
            + item.get("restricted", [])
        )

        for cat in all_categories:
            rule_id = f"{hid}:{cat}"
            source_id = rule_sources.get(cat)

            entry = {
                "rule_id": rule_id,
                "heritage_id": hid,
                "category": cat,
                "source_id": source_id,
                "source_note": source_note if (source_id or source_note) else "",
                "locator": locator if source_id else (locator if source_note else ""),
            }

            if hid in EXCLUDED_HERITAGE:
                excluded[rule_id] = entry
            else:
                candidates[rule_id] = entry

    return candidates, excluded


def run_dry_run(json_path: Path, execute: bool = False):
    """Thực hiện dry-run phân tích đối chiếu DB và rule_base.json."""
    print("=" * 70)
    print("BACKFILL RULE CITATIONS — DRY-RUN AUDIT REPORT (MVP SCOPE)")
    print("=" * 70)

    if not json_path.exists():
        print(f"[ERROR] Không tìm thấy file JSON: {json_path}")
        return

    candidates, excluded = load_rule_base_json(json_path)
    total_json_rules = len(candidates) + len(excluded)
    print(f"[*] Đã đọc {json_path.name}: Tổng cộng {total_json_rules} rules từ 13 di sản.")
    print(f"[*] Di sản bị loại khỏi MVP ({len(EXCLUDED_HERITAGE)} di sản): {', '.join(sorted(EXCLUDED_HERITAGE))} ({len(excluded)} rules)")
    print(f"[*] Tập kỳ vọng trong phạm vi MVP: {len(candidates)} rules từ {len(set(c['heritage_id'] for c in candidates.values()))} di sản.")

    if not get_supabase_client:
        print("[ERROR] Không thể nạp get_supabase_client từ backend/app")
        return

    try:
        client = get_supabase_client()
        resp = client.table("rule_entries").select("*").execute()
        db_rows = resp.data or []
    except Exception as e:
        print(f"[ERROR] Không thể kết nối hoặc truy vấn Supabase live: {type(e).__name__} - {e}")
        return

    print(f"[*] Số dòng hiện tại trong bảng rule_entries trên Supabase: {len(db_rows)}")

    db_map = {r["rule_id"]: r for r in db_rows if "rule_id" in r}

    matched_rules = []
    unmatched_in_scope = []
    overwrite_risk_rows = []
    safe_update_rows = []
    no_change_rows = []

    for rule_id, cand in candidates.items():
        if rule_id in db_map:
            matched_rules.append(rule_id)
            current = db_map[rule_id]
            curr_note = current.get("source_note") or ""
            curr_loc = current.get("locator") or ""
            new_note = cand.get("source_note") or ""
            new_loc = cand.get("locator") or ""

            if cand.get("source_id"):
                if curr_note == new_note and curr_loc == new_loc:
                    no_change_rows.append(rule_id)
                elif curr_note and (curr_note != new_note or (curr_loc and curr_loc != new_loc)):
                    overwrite_risk_rows.append({
                        "rule_id": rule_id,
                        "current_locator": curr_loc,
                        "new_locator": new_loc,
                        "note_diff": curr_note != new_note,
                    })
                else:
                    safe_update_rows.append(rule_id)
        else:
            unmatched_in_scope.append(rule_id)

    print("\n--- KẾT QUẢ THỐNG KÊ ĐỐI CHIẾU ---")
    print(f"- Số rule trong phạm vi MVP khớp 100% với rule_id trong DB: {len(matched_rules)}/{len(candidates)} ({len(matched_rules)/len(candidates)*100:.1f}%)")
    print(f"- Số rule trong phạm vi MVP KHÔNG tìm thấy trong DB: {len(unmatched_in_scope)}")
    print(f"- Số rule bị loại theo quyết định phạm vi MVP (BT003, BT004): {len(excluded)} rules")
    print(f"  + Danh sách chi tiết: {list(excluded.keys())}")

    print(f"\n--- PHÂN TÍCH RỦI RO CẬP NHẬT (Các rule có căn cứ nguồn) ---")
    print(f"- Số dòng có nguy cơ ghi đè: {len(overwrite_risk_rows)}")
    for risk in overwrite_risk_rows:
        print(f"  * [OVERWRITE RISK] {risk['rule_id']}:")
        print(f"    - DB hiện tại (locator lỗi): '{risk['current_locator']}'")
        print(f"    - Giá trị JSON chuẩn:        '{risk['new_locator']}'")
        print(f"    - Khác biệt source_note:     {risk['note_diff']}")
    print(f"- Số dòng cập nhật an toàn (hiện đang rỗng): {len(safe_update_rows)}")
    print(f"- Số dòng đã khớp hoàn toàn (không thay đổi): {len(no_change_rows)}")

    print("\n--- CHẾ ĐỘ THỰC THI ---")
    if not execute:
        print("[DRY-RUN ONLY] Script chạy ở chế độ kiểm tra an toàn.")
        print("[DRY-RUN ONLY] Tuyệt đối KHÔNG INSERT, KHÔNG UPDATE, KHÔNG can thiệp live database.")
        print("[DRY-RUN ONLY] Trạng thái: SẴN SÀNG (Đang chờ xác nhận cuối của người dùng để thực thi).")
    else:
        print("[EXECUTE] Chế độ thực thi live chưa được cấp phép trong phiên này.")

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Dry-run backfill rule citations to Supabase rule_entries (MVP Scope).")
    parser.add_argument("--json-path", type=Path, default=ROOT_DIR / "data" / "rule_base.json", help="Đường dẫn file rule_base.json")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Chạy chế độ dry-run (mặc định)")
    parser.add_argument("--execute", action="store_true", default=False, help="Chạy cập nhật live (cần xác nhận)")
    args = parser.parse_args()

    run_dry_run(args.json_path, execute=args.execute)


if __name__ == "__main__":
    main()
