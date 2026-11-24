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
