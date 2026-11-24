"""Nhập điểm từ file Excel xuất từ Google Form chấm mù vào gói chấm của thí nghiệm, rồi chạy phân tích.

Luồng của repo: tsds/evaluation/experiment.py (lệnh analyze) đọc outputs/experiments/<EXP>/blind/ gồm key.csv và
ratings_<người chấm>.csv. Google Form xuất ra một bảng Excel khác định dạng, nên script này đổi sang định dạng đó:

  1. Đọc file Excel (thư viện chuẩn, không cần openpyxl). Mỗi dòng là một người chấm, bỏ dòng trống.
  2. Đổi cột "Chấm điểm thiết kế k / n (mã Bxxxx) [Tiêu chí]" thành mã ảnh và khóa tiêu chí (config/expert_rubric.json).
  3. Ghi blind/key.csv (từ key.csv của gói form) và blind/ratings_N01.csv, N02, ... (người chấm đánh số theo thứ tự trong file,
     không lưu họ tên hay giờ nộp).
  4. Chạy experiment.analyze: điểm trung bình theo mức và Krippendorff alpha, ghi vào summary.json của thí nghiệm.
  5. Ghi thêm human_report.json: người chấm gần như một mức (độ lệch chuẩn dưới 0,3), kiểm định giữa các mức trên điểm
     trung bình 4 tiêu chí, alpha khi bỏ nhóm người đó và alpha sau khi trừ mức dễ hay khó của từng người.

    uv run python scripts/eval/import_google_form.py outputs/review/google_form_EXP-A/danh_gia_28_nguoi.xlsx

Mặc định thí nghiệm EXP-A và key.csv nằm cạnh file Excel; đổi bằng --exp và --key.
"""
import argparse
import csv
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tsds.evaluation import experiment as E    # noqa: E402

RUBRIC = ROOT / "config" / "expert_rubric.json"
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
HEADER = re.compile(r"\(mã (B\d+)\) \[(.+)\]")
FLAT_SD = 0.3          # người có độ lệch chuẩn điểm dưới mức này coi là chấm gần như một mức


def read_sheet(path: Path) -> list[list[str]]:
    """Đọc sheet đầu tiên của file xlsx thành danh sách dòng (ô rỗng là chuỗi rỗng). Dòng trống hoàn toàn trả về []."""
    z = zipfile.ZipFile(path)
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS):
            shared.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["m"])))
    sheet = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))

    def col(ref: str) -> int:                       # "AB3" thành 27
        n = 0
        for ch in re.match(r"[A-Z]+", ref).group():
            n = n * 26 + ord(ch) - 64
        return n - 1

    rows = []
    for r in sheet.iter("{%s}row" % NS["m"]):
        cells = {}
        for c in r.findall("m:c", NS):
            v, kind = c.find("m:v", NS), c.get("t")
            if kind == "inlineStr":
                cells[col(c.get("r"))] = "".join(t.text or "" for t in c.iter("{%s}t" % NS["m"]))
            elif v is not None:
                cells[col(c.get("r"))] = shared[int(v.text)] if kind == "s" else v.text
        rows.append([cells.get(i, "") for i in range(max(cells) + 1)] if cells else [])
    return rows


def parse_score(text: str) -> int | None:
    """Lấy điểm 1 đến 5 từ ô dạng '4 - Tốt'. Ô rỗng hoặc không đúng dạng thì trả None."""
    m = re.match(r"\s*([1-5])\b", text or "")
    return int(m.group(1)) if m else None


def parse_responses(rows: list[list[str]], label_to_key: dict[str, str]) -> tuple[list[str], list[dict]]:
    """Trả về (danh sách mã ảnh, danh sách người chấm). Mỗi người là dict {(mã, khóa tiêu chí): điểm hoặc None}."""
    head = rows[0]
    cols: dict[int, tuple[str, str]] = {}
    for i, h in enumerate(head):
        m = HEADER.search(h)
        if m:
            if m.group(2) not in label_to_key:
                raise ValueError(f"Tiêu chí {m.group(2)!r} không có trong config/expert_rubric.json")
            cols[i] = (m.group(1), label_to_key[m.group(2)])
    if not cols:
        raise ValueError("Không thấy cột điểm nào có dạng '(mã Bxxxx) [Tiêu chí]'")
    codes = sorted({c for c, _ in cols.values()})
    raters = []
    for row in rows[1:]:
        if not any(x.strip() for x in row):
            continue                                # dòng trống ở cuối bảng Google Form
        row = row + [""] * (len(head) - len(row))
        raters.append({cols[i]: parse_score(row[i]) for i in cols})
    return codes, raters


def write_blind(exp_dir: Path, google_key: Path, codes: list[str], raters: list[dict], keys: list[str]) -> Path:
    """Ghi blind/key.csv và blind/ratings_N<số>.csv theo định dạng mà experiment.analyze đọc."""
    blind = exp_dir / "blind"
    blind.mkdir(parents=True, exist_ok=True)
    for old in blind.glob("ratings_*.csv"):
        old.unlink()                                 # tránh lẫn phiếu của lần nhập trước
    gk = {r["code"]: r for r in csv.DictReader(google_key.open(encoding="utf-8-sig"))}
    missing = [c for c in codes if c not in gk]
    if missing:
        raise ValueError(f"Mã ảnh không có trong {google_key.name}: {missing[:5]}")
    with (blind / "key.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["code", "run_key", "heritage_id", "iv_level", "replicate"])
        for c in codes:
            w.writerow([c, gk[c]["run_key"], gk[c]["heritage_id"], gk[c]["controlnet_weight"], gk[c]["seed"]])
    for n, scores in enumerate(raters, start=1):
        rid = f"N{n:02d}"
        with (blind / f"ratings_{rid}.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["rater_id", "code", "heritage_reference"] + keys + ["comment"])
            for c in codes:
                w.writerow([rid, c, gk[c]["heritage_id"]] + ["" if scores[(c, k)] is None else scores[(c, k)] for k in keys]
                           + [""])
    return blind


def human_report(codes: list[str], raters: list[dict], keys: list[str], levels: dict[str, str],
                 blocks: dict[str, tuple]) -> dict:
    """Số liệu bổ sung ngoài experiment.analyze. levels: mã ảnh thành mức; blocks: mã ảnh thành (hiện vật, seed)."""
    S = np.array([[[r[(c, k)] if r[(c, k)] is not None else np.nan for c in codes] for k in keys] for r in raters], float)
    # S[người, tiêu chí, ảnh]
    per_rater = np.nanmean(S, axis=(1, 2))
    sd = np.nanstd(S.reshape(len(raters), -1), axis=1)
    flat = [i for i in range(len(raters)) if sd[i] < FLAT_SD]
    level_list = sorted(set(levels.values()), key=float, reverse=True)

    def block_means(idx: list[int]) -> dict:
        """Điểm trung bình (người trong idx, 4 tiêu chí) của từng ảnh, gom theo khối (hiện vật, seed) và mức."""
        out: dict = {}
        for j, c in enumerate(codes):
            out.setdefault(blocks[c], {})[levels[c]] = float(np.nanmean(S[idx, :, j]))
        return out

    def tests(idx: list[int]) -> dict:
        b = [v for v in block_means(idx).values() if all(lv in v for lv in level_list)]
        res = {"n_blocks": len(b), "mean_by_level": {lv: round(float(np.mean([x[lv] for x in b])), 3) for lv in level_list}}
        try:
            from scipy import stats                  # noqa: PLC0415
        except ImportError:                          # pragma: no cover
            return res
        if len(b) >= 3 and len(level_list) >= 3:
            f = stats.friedmanchisquare(*[[x[lv] for x in b] for lv in level_list])
            res["friedman_p"] = float(f"{f.pvalue:.3g}")      # 3 chữ số có nghĩa, p rất nhỏ không bị làm tròn về 0
        ctrl = level_list[0]
        res["wilcoxon_p_vs_" + ctrl] = {
            lv: float(f"{stats.wilcoxon([x[lv] - x[ctrl] for x in b]).pvalue:.3g}")
            for lv in level_list[1:] if len(b) >= 6 and any(x[lv] != x[ctrl] for x in b)}
        return res

    def alpha(idx: list[int], centered: bool = False) -> float | None:
        m = S[idx].transpose(0, 2, 1).reshape(len(idx), -1)      # [người, ảnh x tiêu chí]
        if centered:
            m = m - np.nanmean(m, axis=1, keepdims=True)
        a = E.krippendorff_alpha_interval([[None if np.isnan(v) else float(v) for v in row] for row in m])
        return None if np.isnan(a) else round(a, 3)

    everyone = list(range(len(raters)))
    keep = [i for i in everyone if i not in flat]
    return {"n_raters": len(raters), "flat_raters": [f"N{i + 1:02d}" for i in flat],
            "rater_means": [round(float(x), 2) for x in per_rater],
            "all_raters": {"alpha": alpha(everyone), "alpha_centered": alpha(everyone, True), **tests(everyone)},
            "without_flat_raters": {"n": len(keep), "alpha": alpha(keep) if len(keep) > 1 else None, **tests(keep)}}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Nhập điểm Google Form (xlsx) vào gói chấm của thí nghiệm và phân tích")
    ap.add_argument("xlsx", type=Path, help="file Excel xuất từ tab Câu trả lời của Google Form")
    ap.add_argument("--exp", default="EXP-A", help="mã thí nghiệm (mặc định EXP-A)")
    ap.add_argument("--key", type=Path, default=None, help="key.csv của gói form (mặc định: cạnh file Excel)")
    args = ap.parse_args(argv)

    rubric = json.loads(RUBRIC.read_text(encoding="utf-8"))["criteria"]
    label_to_key = {c["label"]: c["key"] for c in rubric}
    exp_dir = ROOT / "outputs" / "experiments" / args.exp
    keys = json.loads((exp_dir / "spec.json").read_text(encoding="utf-8"))["metrics"]["human"]

    codes, raters = parse_responses(read_sheet(args.xlsx), label_to_key)
    blind = write_blind(exp_dir, args.key or args.xlsx.parent / "key.csv", codes, raters, keys)
    key_rows = {r["code"]: r for r in csv.DictReader((blind / "key.csv").open(encoding="utf-8"))}
    summary = E.analyze(exp_dir)
    report = human_report(codes, raters, keys, {c: key_rows[c]["iv_level"] for c in codes},
                          {c: (key_rows[c]["heritage_id"], key_rows[c]["replicate"]) for c in codes})
    report["agreement_by_criterion"] = summary["agreement"]
    (exp_dir / "human_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(raters)} người chấm, {len(codes)} ảnh, tiêu chí: {', '.join(keys)}")
    print(f"alpha từng tiêu chí: {summary['agreement']}")
    print(f"người chấm gần như một mức: {report['flat_raters']}")
    print(f"ghi {blind.relative_to(ROOT)}, summary.json, human_report.json")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
