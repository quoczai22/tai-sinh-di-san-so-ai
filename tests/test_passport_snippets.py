"""Kiểm thử scripts/docs/build_passport_snippets.py: chia khóa cấp cao, chia phần tử mảng, ngắt dòng không mất chữ."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("passport_snippets", ROOT / "scripts" / "docs" / "build_passport_snippets.py")
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)

DOC = {"schema": "x", "heritage": {"name": "Gốm"}, "process_steps": [{"step": "a", "inputs": []}, {"step": "b", "inputs": ["h1"]},
       {"step": "c", "inputs": []}], "rights": {"allowed": True}}
LINES = json.dumps(DOC, ensure_ascii=False, indent=2).splitlines()


def test_top_level_ranges_cover_each_key_without_gaps():
    r = S.top_level_ranges(LINES)
    assert list(r) == ["schema", "heritage", "process_steps", "rights"]
    first, last = r["rights"]
    assert LINES[first - 1].startswith('  "rights"') and LINES[last - 1] == "  }"      # dòng cuối của file là dấu } cấp ngoài
    for (a, b), (c, d) in zip(list(r.values()), list(r.values())[1:]):
        assert c == b + 1 and a <= b


def test_item_ranges_finds_every_step():
    first, last = S.top_level_ranges(LINES)["process_steps"]
    items = S.item_ranges(LINES, first, last)
    assert len(items) == 3
    for a, b in items:
        assert LINES[a - 1].strip() == "{" and LINES[b - 1].strip().rstrip(",") == "}"
    assert LINES[items[1][0]].strip() == '"step": "b",'


def test_wrap_line_loses_nothing_and_respects_width():
    line = '    "reason": "' + "Trọng số LoRA áo dài được huấn luyện từ ảnh VietFashion " * 6 + '"'
    cuts = S.wrap_line(line, 60)
    assert "".join(line[i:j] for i, j in cuts) == line
    assert all(j - i <= 60 for i, j in cuts)
    assert all(line[j - 1] == " " for _, j in cuts[:-1])                 # ngắt sau khoảng trắng, không cắt giữa từ


def test_wrap_line_hard_breaks_a_word_longer_than_width():
    line = "a" * 130
    assert [j - i for i, j in S.wrap_line(line, 50)] == [50, 50, 30]


def test_short_and_empty_lines_stay_whole():
    assert S.wrap_line("abc", 50) == [(0, 3)]
    assert S.wrap_line("", 50) == [(0, 0)]


def test_char_kinds_colors_whole_string_and_keeps_digits_in_strings_as_strings():
    line = '  "id": "LR3D_33", "n": 12, "ok": true, "x": null'
    kinds = S.char_kinds(line)
    assert len(kinds) == len(line)
    assert kinds[line.index("LR3D")] == "str" and kinds[line.index("33")] == "str"     # chữ số trong chuỗi không bị tô như số
    assert kinds[line.index("12")] == "num" and kinds[line.index("true")] == "lit" and kinds[line.index('"id"')] == "key"


def test_item_label_names_each_kind_of_new_entry():
    assert S.item_label({"seq": 7, "event": "approval:qa_warning"}) == "#7 approval:qa_warning"
    assert S.item_label({"edit_id": "E1"}) == "E1" and S.item_label({"step": "manual_edit"}) == "manual_edit"
    assert S.item_label({"version": 2, "kind": "human_edit"}) == "v2 human_edit"
    assert S.item_label({"path": "outputs/edits/x.png"}) == "outputs/edits/x.png"


def test_describe_diff_reports_new_items_and_changed_fields_only():
    old = {"run_id": "R1", "edits": [], "versions": [{"version": 1, "kind": "ai_generated"}], "ledger": [{"seq": 1, "event": "a"}],
           "quality": {"overall": {"decision": "PASS"}, "evaluated_at": "t1"}, "approval": {"status": "pending_expert_review"}}
    new = {"run_id": "R1", "edits": [{"edit_id": "E1"}],
           "versions": [{"version": 1, "kind": "ai_generated"}, {"version": 2, "kind": "human_edit"}],
           "ledger": [{"seq": 1, "event": "a"}, {"seq": 2, "event": "version:human_edit"}],
           "quality": {"overall": {"decision": "WARN"}, "evaluated_at": "t1"}, "approval": {"status": "qa_warning"}}
    text = "\n".join(S.describe_diff(old, new))
    assert "edits: 0 thành 1 mục, mục mới: E1" in text and "v2 human_edit" in text and "#2 version:human_edit" in text
    assert "quality.overall.decision: 'PASS' thành 'WARN'" in text and "approval.status" in text
    assert "evaluated_at" not in text and "run_id" not in text              # trường không đổi thì không in


def test_describe_diff_is_empty_for_identical_passports():
    doc = {"edits": [], "quality": {"a": 1}, "approval": {"status": "x"}}
    assert S.describe_diff(doc, json.loads(json.dumps(doc))) == []



def test_split_ranges_cover_all_lines_in_order_and_cut_at_keys():
    doc = {"quality": {"G2": {"gate": "G2", "metrics": {"a": 1, "b": 2}, "details": {"x": 1}}, "G3": {"gate": "G3", "metrics": {"c": 3},
           "details": {"y": 2, "z": 3}}, "overall": {"decision": "PASS"}}}
    lines = json.dumps(doc, ensure_ascii=False, indent=2).splitlines()
    first, last = S.top_level_ranges(lines)["quality"]
    parts = S.split_ranges(lines, first, last, 3)
    assert len(parts) == 3 and parts[0][0] == first and parts[-1][1] == last
    for (a, b), (c, d) in zip(parts, parts[1:]):
        assert c == b + 1 and a <= b                                          # liền nhau, không sót dòng nào
    for a, _ in parts[1:]:
        assert lines[a - 1].lstrip().startswith('"')                            # đoạn sau bắt đầu ở một khóa, không giữa dấu đóng ngoặc


def test_render_columns_makes_one_wide_sheet_with_equal_height_panels(tmp_path):
    lines = json.dumps({"quality": {f"k{i}": {"v": i} for i in range(9)}}, indent=2).splitlines()
    first, last = S.top_level_ranges(lines)["quality"]
    path = tmp_path / "q.png"
    parts = S.render_columns(lines, first, last, path)
    from PIL import Image
    img = Image.open(path)
    assert len(parts) == 3 and img.width > 2 * img.height / 3 and img.width > 1500


def test_render_grid_puts_three_panels_per_row(tmp_path):
    lines = json.dumps({"process_steps": [{"step": f"s{i}", "note": "x" * (i * 10)} for i in range(7)]}, indent=2).splitlines()
    first, last = S.top_level_ranges(lines)["process_steps"]
    steps = S.item_ranges(lines, first, last)
    path = tmp_path / "g.png"
    S.render_grid(lines, steps, path)
    from PIL import Image
    img = Image.open(path)
    one = S.draw(lines, *steps[0], wrap=70)
    assert len(steps) == 7 and img.width >= 3 * one.width                      # hàng đầy có 3 ô
    assert img.height >= 3 * one.height - 1                                     # 7 bước thành 3 hàng (3, 3, 1)


def test_item_ranges_works_on_a_ledger_and_tail_keeps_the_last_entries():
    doc = {"ledger": [{"seq": i, "event": f"e{i}", "prev_hash": "p" * 8} for i in range(1, 6)], "rights": {}}
    lines = json.dumps(doc, indent=2).splitlines()
    first, last = S.top_level_ranges(lines)["ledger"]
    tail = S.item_ranges(lines, first, last)[-3:]
    assert len(tail) == 3 and '"seq": 3' in lines[tail[0][0]] and '"seq": 5' in lines[tail[-1][0]]


def test_render_before_after_checks_hashes_against_the_passport(tmp_path, monkeypatch):
    from PIL import Image
    monkeypatch.setattr(S, "ROOT", tmp_path)
    for name, color in (("before.png", "white"), ("after.png", "red")):
        Image.new("RGB", (40, 60), color).save(tmp_path / name)
    doc = {"versions": [{"path": "before.png", "sha256": S.sha256_of(tmp_path / "before.png")}],
           "edits": [{"edit_id": "E1", "before_sha256": S.sha256_of(tmp_path / "before.png"), "after_path": "after.png",
                      "after_sha256": S.sha256_of(tmp_path / "after.png")}]}
    assert S.render_before_after(doc, tmp_path, S.DARK) == ["  before_sha256: KHỚP", "  after_sha256: KHỚP"]
    assert Image.open(tmp_path / "anh_truoc_sau.png").size[0] > 80 and (tmp_path / "ma_bam_truoc_sau.png").is_file()
    doc["edits"][0]["after_sha256"] = "0" * 64                                   # mã trong Passport lệch tệp thật: phải báo
    assert S.render_before_after(doc, tmp_path, S.DARK)[1] == "  after_sha256: KHÔNG KHỚP"
