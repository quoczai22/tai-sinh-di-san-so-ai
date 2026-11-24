"""Kiểm thử scripts/eval/import_google_form.py bằng một file Excel giả nhỏ, không cần GPU hay dữ liệu thật.

Đáp án tính tay: 3 người chấm 4 ảnh (hai hiện vật, mỗi hiện vật hai mức 0,85 và 0,25), mỗi người cho cả 4 tiêu chí cùng một điểm
cho mỗi ảnh. Điểm các ảnh B1 đến B4: người 1 và 2 chấm 5, 3, 5, 3; người 3 chấm 4, 2, 4, 2.
  mức 0,85: (5+5+4+5+5+4)/6 = 4,6667     mức 0,25: (3+3+2+3+3+2)/6 = 2,6667
  Krippendorff alpha: sai khác trong từng ảnh trung bình 0,6667, sai khác chung 2,6667, nên alpha = 1 - 0,6667/2,6667 = 0,75.
"""
import csv
import importlib.util
import json
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("import_google_form", ROOT / "scripts" / "eval" / "import_google_form.py")
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)

LABELS = ["Nhận ra họa tiết gốc", "Phù hợp văn hoá", "Thẩm mỹ thiết kế", "Toàn vẹn dáng áo dài"]
KEYS = ["motif_recognizability", "cultural_appropriateness", "aesthetic", "garment_integrity"]
CODES = ["B1", "B2", "B3", "B4"]
SCORES = {"4": "4 - Tốt", "5": "5 - Rất tốt", "3": "3 - Chấp nhận được", "2": "2 - Kém"}
RATER_SCORES = [[5, 3, 5, 3], [5, 3, 5, 3], [4, 2, 4, 2]]


def _col(i: int) -> str:
    name = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        name = chr(65 + r) + name
    return name


def _write_xlsx(path: Path, rows: list[list[str]]) -> None:
    """Ghi xlsx tối thiểu, ô chữ dạng inlineStr; dòng rỗng ([]) thành dòng không có ô."""
    out = []
    for r, row in enumerate(rows, start=1):
        cells = "".join(f'<c r="{_col(i)}{r}" t="inlineStr"><is><t>{escape(v)}</t></is></c>'
                        for i, v in enumerate(row) if v != "")
        out.append(f'<row r="{r}">{cells}</row>')
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("xl/workbook.xml", f'<workbook xmlns="{ns}"><sheets><sheet name="s" sheetId="1"/></sheets></workbook>')
        z.writestr("xl/worksheets/sheet1.xml", f'<worksheet xmlns="{ns}"><sheetData>{"".join(out)}</sheetData></worksheet>')


def _rows(rater_scores=RATER_SCORES, labels=LABELS) -> list[list[str]]:
    head = ["Dấu thời gian", "Bạn là"]
    for k, code in enumerate(CODES, start=1):
        head += [f"Chấm điểm thiết kế {k} / 4 (mã {code}) [{lb}]" for lb in labels]
    rows = [head]
    for n, sc in enumerate(rater_scores):
        rows.append([str(46000 + n), "Người quan tâm"] + [SCORES[str(s)] for s in sc for _ in labels])
        rows.append([])                                     # dòng trống xen giữa, như file thật có 9 dòng trống
    return rows


def _google_key(path: Path) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["version", "role", "position", "code", "heritage_id", "controlnet_weight", "seed", "run_key"])
        for i, (code, het, wt) in enumerate(zip(CODES, ["H1", "H1", "H2", "H2"], ["0.85", "0.25", "0.85", "0.25"]), start=1):
            w.writerow(["A", "", i, code, het, wt, 42, f"EXP-T|{het}|controlnet_weight={wt}|seed=42"])


def test_parse_score():
    assert M.parse_score("4 - Tốt") == 4
    assert M.parse_score(" 1 - Rất kém") == 1
    assert M.parse_score("") is None and M.parse_score("6 - ?") is None and M.parse_score("Tốt") is None


def test_read_sheet_handles_inline_strings_and_blank_rows(tmp_path):
    f = tmp_path / "a.xlsx"
    _write_xlsx(f, [["x", "", "z"], [], ["1", "2"]])
    assert M.read_sheet(f) == [["x", "", "z"], [], ["1", "2"]]


def test_parse_responses_maps_labels_and_skips_blank_rows():
    label_to_key = dict(zip(LABELS, KEYS))
    codes, raters = M.parse_responses(_rows(), label_to_key)
    assert codes == CODES and len(raters) == 3
    assert raters[0][("B1", "aesthetic")] == 5 and raters[2][("B2", "garment_integrity")] == 2


def test_parse_responses_rejects_unknown_criterion():
    with pytest.raises(ValueError, match="không có trong"):
        M.parse_responses(_rows(labels=["Tiêu chí lạ"] * 4), dict(zip(LABELS, KEYS)))


def test_missing_score_becomes_none():
    rows = _rows()
    rows[1][2] = ""                                          # người 1 bỏ trống ô đầu
    _, raters = M.parse_responses(rows, dict(zip(LABELS, KEYS)))
    assert raters[0][("B1", "motif_recognizability")] is None


def test_write_blind_rejects_code_missing_from_key(tmp_path):
    _google_key(tmp_path / "key.csv")
    with pytest.raises(ValueError, match="không có trong"):
        M.write_blind(tmp_path, tmp_path / "key.csv", CODES + ["B9"], [], KEYS)


def test_end_to_end_matches_hand_computed_values(tmp_path, monkeypatch):
    exp = tmp_path / "outputs" / "experiments" / "EXP-T"
    exp.mkdir(parents=True)
    (exp / "spec.json").write_text(json.dumps({
        "id": "EXP-T", "metrics": {"automatic": [], "human": KEYS},
        "independent_variable": {"name": "controlnet_weight", "levels": [0.85, 0.25]}}), encoding="utf-8")
    (exp / "results.csv").write_text("run_key,iv_level\n", encoding="utf-8")
    xlsx = tmp_path / "form" / "danh_gia.xlsx"
    xlsx.parent.mkdir()
    _write_xlsx(xlsx, _rows())
    _google_key(xlsx.parent / "key.csv")
    monkeypatch.setattr(M, "ROOT", tmp_path)
    assert M.main([str(xlsx), "--exp", "EXP-T"]) == 0

    # định dạng gói chấm mà experiment.analyze đọc
    ratings = list(csv.DictReader((exp / "blind" / "ratings_N01.csv").open(encoding="utf-8")))
    assert [r["code"] for r in ratings] == CODES and ratings[0]["aesthetic"] == "5" and ratings[1]["aesthetic"] == "3"
    key = list(csv.DictReader((exp / "blind" / "key.csv").open(encoding="utf-8")))
    assert key[1]["iv_level"] == "0.25" and key[1]["heritage_id"] == "H1" and key[1]["replicate"] == "42"
    assert len(list((exp / "blind").glob("ratings_*.csv"))) == 3

    summary = json.loads((exp / "summary.json").read_text(encoding="utf-8"))
    assert summary["human"]["aesthetic"]["0.85"]["mean"] == pytest.approx(4.6667, abs=1e-4)
    assert summary["human"]["aesthetic"]["0.25"]["mean"] == pytest.approx(2.6667, abs=1e-4)
    assert summary["agreement"]["aesthetic"] == pytest.approx(0.75, abs=1e-3)

    report = json.loads((exp / "human_report.json").read_text(encoding="utf-8"))
    assert report["n_raters"] == 3 and report["flat_raters"] == []
    # Gộp 4 tiêu chí thành 48 giá trị (mỗi giá trị lặp 4 lần): tổng bình phương lệch 4 x 14,667 = 58,667,
    # sai khác chung = 2 x 58,667 / 47 = 2,4965, nên alpha = 1 - 0,6667 / 2,4965 = 0,733 (khác 0,75 do hiệu chỉnh cỡ mẫu)
    assert report["all_raters"]["alpha"] == pytest.approx(0.733, abs=1e-3)
    assert report["all_raters"]["mean_by_level"] == {"0.85": pytest.approx(4.667, abs=1e-3),
                                                      "0.25": pytest.approx(2.667, abs=1e-3)}


def test_human_report_flags_rater_who_gives_one_score():
    label_to_key = dict(zip(LABELS, KEYS))
    codes, raters = M.parse_responses(_rows([[5, 3, 5, 3], [5, 5, 5, 5], [4, 2, 4, 2]]), label_to_key)
    levels = {"B1": "0.85", "B2": "0.25", "B3": "0.85", "B4": "0.25"}
    blocks = {"B1": ("H1", "42"), "B2": ("H1", "42"), "B3": ("H2", "42"), "B4": ("H2", "42")}
    rep = M.human_report(codes, raters, KEYS, levels, blocks)
    assert rep["flat_raters"] == ["N02"] and rep["without_flat_raters"]["n"] == 2
