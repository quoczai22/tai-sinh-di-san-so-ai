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

def run_execute(json_path: Path):
    """Thực thi UPDATE an toàn trên live DB cho 11 di sản thuộc MVP."""
    print("=" * 70)
    print("BACKFILL RULE CITATIONS — LIVE EXECUTION")
    print("=" * 70)

    candidates, excluded = load_rule_base_json(json_path)
    client = get_supabase_client()
    resp = client.table("rule_entries").select("*").execute()
    db_rows = resp.data or []
    db_map = {r["rule_id"]: r for r in db_rows if "rule_id" in r}

    updated_count = 0
    skipped_count = 0

    for rule_id, cand in candidates.items():
        if rule_id in db_map:
            current = db_map[rule_id]
            curr_note = current.get("source_note") or ""
            curr_loc = current.get("locator") or ""
            new_note = cand.get("source_note") or ""
            new_loc = cand.get("locator") or ""

            # Chỉ cập nhật khi có căn cứ nguồn (cand có source_id) và có sự khác biệt
            if cand.get("source_id"):
                if curr_note != new_note or curr_loc != new_loc:
                    print(f"[*] Đang cập nhật {rule_id}:")
                    print(f"    - Locator cũ: '{curr_loc}' -> Locator mới: '{new_loc}'")
                    client.table("rule_entries").update({
                        "source_note": new_note,
                        "locator": new_loc,
                    }).eq("rule_id", rule_id).execute()
                    updated_count += 1
                else:
                    skipped_count += 1

    print(f"\n[EXECUTION COMPLETED] Số dòng đã UPDATE: {updated_count} | Số dòng giữ nguyên: {skipped_count}")


def run_verify():
    """Kiểm tra và xác minh trạng thái live DB sau khi đối chiếu/backfill."""
    print("=" * 70)
    print("BACKFILL RULE CITATIONS — POST-AUDIT & VERIFICATION")
    print("=" * 70)

    client = get_supabase_client()
    resp = client.table("rule_entries").select("*").order("rule_id").execute()
    rows = resp.data or []

    not_null_notes = [r for r in rows if r.get("source_note")]
    null_notes = [r for r in rows if not r.get("source_note")]

    print(f"- Tổng số dòng trong rule_entries: {len(rows)}")
    print(f"- Số dòng có source_note != NULL: {len(not_null_notes)}")
    print(f"- Số dòng có source_note == NULL: {len(null_notes)}")

    print("\n- Chi tiết các dòng có căn cứ trích dẫn (source_note != NULL):")
    for r in not_null_notes:
        loc_snippet = (r.get("locator") or "")[:60]
        print(f"  * {r['rule_id']}: source_id={r.get('source_id')} | locator='{loc_snippet}...'")

    # Mẫu kiểm tra BT005
    bt005_rows = [r for r in rows if r.get("heritage_id") == "BT005" and r.get("category") == "core_motif"]
    if bt005_rows:
        bt005 = bt005_rows[0]
        print("\n- Kiểm tra mẫu BT005:core_motif:")
        print(f"  + rule_id: {bt005.get('rule_id')}")
        print(f"  + source_id: {bt005.get('source_id')}")
        print(f"  + locator: '{bt005.get('locator')}'")
        print(f"  + source_note snippet: '{str(bt005.get('source_note'))[:80]}...'")

    # Test RPC get_rule_base cho BT001 và BT005
    print("\n- Kiểm tra RPC get_rule_base qua Supabase:")
    for hid in ("BT001", "BT005"):
        rpc_res = client.rpc("get_rule_base", {"p_heritage_id": hid}).execute()
        data = rpc_res.data
        if data:
            print(f"  + get_rule_base('{hid}') -> OK (preserve: {data.get('preserve')}, locators keys: {list(data.get('locators', {}).keys())})")
        else:
            print(f"  + get_rule_base('{hid}') -> NULL/FAIL")

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Dry-run and verification for backfill rule citations to Supabase rule_entries (MVP Scope).")
    parser.add_argument("--json-path", type=Path, default=ROOT_DIR / "data" / "rule_base.json", help="Đường dẫn file rule_base.json")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Chạy chế độ dry-run")
    parser.add_argument("--execute", action="store_true", default=False, help="Chạy cập nhật live")
    parser.add_argument("--verify", action="store_true", default=False, help="Chạy kiểm tra sau cập nhật")
    args = parser.parse_args()

    if args.verify:
        run_verify()
    elif args.execute:
        run_execute(args.json_path)
    else:
        # Mặc định là dry-run
        run_dry_run(args.json_path, execute=False)


if __name__ == "__main__":
    main()
