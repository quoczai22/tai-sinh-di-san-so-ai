"""Xuất phiếu nhận xét chuyên gia ra file Word (.docx) từ gói phiếu chuyên gia đã dựng.

Đầu vào: thư mục gói do `build_google_form.py --audience expert` dựng (form_spec.json và images/).
Đầu ra: mỗi vai một file .docx trong <gói>/docx/ (di sản, thiết kế), dùng chung 12 ảnh. Mỗi thiết kế một trang:
ảnh ghép, bảng chấm điểm (ô tích bấm được), quyết định Đạt / Cần chỉnh sửa / Loại (bỏ nếu spec không có `decisions`,
như phiếu một người của `--single`), ô nhận xét.

Ô tích là điều khiển nội dung (content control) của Word, bấm là tích được. Mỗi ô có thẻ ẩn dạng
"mã ảnh|tiêu chí|điểm" (ví dụ "B1234|aesthetic|4"), để sau này đọc kết quả tự động từ file chuyên gia gửi lại.
Thẻ chỉ chứa mã ảnh và tên tiêu chí, không có trọng số, seed hay tên cách tạo.

    uv run python scripts/eval/build_expert_docx.py
    uv run python scripts/eval/build_expert_docx.py --package outputs/review/google_form_EXP-A_expert
"""
import argparse
import json
import sys
import unicodedata
from pathlib import Path
from xml.sax.saxutils import quoteattr

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[2]
DECISIONS = [("approve", "Đạt"), ("revise", "Cần chỉnh sửa"), ("reject", "Loại")]    # khóa khớp config/expert_rubric.json
IMAGE_WIDTH_CM = 12.0
FONT = "Arial"
W_NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml"')


def slug(text: str) -> str:
    """Tên tệp không dấu: 'chuyên gia di sản' -> 'chuyen_gia_di_san'."""
    s = unicodedata.normalize("NFD", text.replace("đ", "d").replace("Đ", "D"))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return "_".join("".join(c if c.isalnum() else " " for c in s).lower().split())


def add_checkbox(par, tag: str, label: str = "") -> None:
    """Thêm một ô tích bấm được của Word vào đoạn văn, kèm chữ nhãn phía sau nếu có."""
    xml = (f'<w:sdt {W_NS}><w:sdtPr><w:tag w:val={quoteattr(tag)}/>'
           '<w14:checkbox><w14:checked w14:val="0"/><w14:checkedState w14:val="2612" w14:font="MS Gothic"/>'
           '<w14:uncheckedState w14:val="2610" w14:font="MS Gothic"/></w14:checkbox></w:sdtPr>'
           '<w:sdtContent><w:r><w:rPr><w:rFonts w:ascii="MS Gothic" w:eastAsia="MS Gothic" w:hAnsi="MS Gothic" w:hint="eastAsia"/>'
           '<w:sz w:val="26"/></w:rPr><w:t>☐</w:t></w:r></w:sdtContent></w:sdt>')
    par._p.append(parse_xml(xml))
    if label:
        par.add_run(" " + label)


def set_cell_width(cell, cm: float) -> None:
    cell.width = Cm(cm)


def fix_widths(table, widths_cm: list[float]) -> None:
    """Đặt độ rộng cột ở cả ô và lưới cột, tắt tự co: Word đọc độ rộng ô, LibreOffice và Google Docs đọc lưới cột."""
    table.autofit = False
    for gc, w in zip(table._tbl.tblGrid.findall(qn("w:gridCol")), widths_cm):
        gc.set(qn("w:w"), str(int(w * 567)))
    for row in table.rows:
        for cell, w in zip(row.cells, widths_cm):
            cell.width = Cm(w)


def style_run(run, size: float | None = None, bold: bool = False, italic: bool = False, color: tuple | None = None) -> None:
    if size:
        run.font.size = Pt(size)
    run.bold, run.italic = bold, italic
    if color:
        run.font.color.rgb = RGBColor(*color)


def add_text_cell(cell, text: str, size: float = 10, bold: bool = False, italic: bool = False, center: bool = False) -> None:
    par = cell.paragraphs[0]
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER if center else WD_ALIGN_PARAGRAPH.LEFT
    style_run(par.add_run(text), size, bold, italic)


def add_box(doc, min_height_cm: float) -> None:
    """Ô trống rộng cả trang để chuyên gia gõ nhận xét."""
    t = doc.add_table(rows=1, cols=1)
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    fix_widths(t, [17.0])
    tr_pr = t.rows[0]._tr.get_or_add_trPr()
    tr_pr.append(parse_xml(f'<w:trHeight {W_NS} w:val="{int(min_height_cm * 567)}" w:hRule="atLeast"/>'))


def build_doc(spec: dict, version: dict, images_dir: Path) -> Document:
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)                     # A4 (mặc định của python-docx là Letter)
    sec.left_margin = sec.right_margin = sec.top_margin = sec.bottom_margin = Cm(2)
    normal = doc.styles["Normal"]
    normal.font.name, normal.font.size = FONT, Pt(11)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    normal.element.rPr.append(parse_xml(f'<w:lang {W_NS} w:val="vi-VN" w:eastAsia="vi-VN"/>'))
    for name, size in (("Title", 20), ("Heading 1", 14), ("Heading 2", 13)):
        st = doc.styles[name]
        st.font.name, st.font.size, st.font.bold = FONT, Pt(size), True
        st.font.color.rgb = RGBColor(29, 42, 54)
        rf = st.element.rPr.rFonts
        for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
            rf.attrib.pop(qn(attr), None)                                   # bỏ phông theme, không thì tiêu đề không theo Arial
        for attr in ("w:ascii", "w:hAnsi", "w:eastAsia"):
            rf.set(qn(attr), FONT)
    doc.core_properties.author = ""                                         # python-docx ghi tên mặc định, xóa đi
    doc.core_properties.title = spec["title"]
    doc.core_properties.comments = ""                                       # xóa mô tả mặc định "generated by python-docx"

    doc.add_heading(spec["title"], level=0)
    p = doc.add_paragraph()
    style_run(p.add_run("Phiếu dành cho " + version["label"]), 12, bold=True, color=(30, 63, 122))
    doc.add_paragraph(version["intro"])

    doc.add_heading("Cách điền", level=1)
    decide = bool(spec.get("decisions"))                                    # phiếu cho một người có thể không có hàng quyết định
    lines = ["Mở file bằng Microsoft Word trên máy tính để bấm được ô tích (Word web, Google Docs, WPS có thể không bấm được).",
             "Bấm vào ô vuông để tích chọn. Bấm lần nữa để bỏ chọn. Mỗi tiêu chí chỉ chọn một điểm"
             + (", mỗi thiết kế chỉ chọn một quyết định." if decide else "."),
             "Gõ nhận xét vào ô trống bên dưới mỗi thiết kế."
             + (" Chọn Cần chỉnh sửa hoặc Loại thì nên ghi lý do." if decide else ""),
             "Điền xong, lưu file và gửi lại cho nhóm. Không đổi tên mục hay xóa ô nào."]
    for line in lines:
        doc.add_paragraph(line, style="List Bullet")
    scale = " | ".join(spec["scale"])
    p = doc.add_paragraph()
    style_run(p.add_run("Thang điểm: "), bold=True)
    p.add_run(scale)

    doc.add_heading("Thông tin người thẩm định", level=1)
    texts = [q for q in spec["profile"] if q["type"] == "text"]
    if texts:                                                               # bảng không có hàng nào làm Word báo lỗi
        info = doc.add_table(rows=len(texts), cols=2)
        info.style = "Table Grid"
        fix_widths(info, [6.0, 11.0])
        for q, row in zip(texts, info.rows):
            add_text_cell(row.cells[0], q["title"], bold=True)
    for q in spec["profile"]:
        if q["type"] == "choice":
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(10)
            style_run(p.add_run(q["title"]), bold=True)
            for i, choice in enumerate(q["choices"]):
                add_checkbox(doc.add_paragraph(), f"profile|consent|{i}", choice)

    items = version["items"]
    for n, item in enumerate(items, start=1):
        head = doc.add_heading(f"Thiết kế {n} / {len(items)} (mã {item['code']})", level=2)
        head.paragraph_format.page_break_before = True                      # mỗi thiết kế một trang, không cần đoạn rỗng
        doc.add_picture(str(images_dir / item["file"]), width=Cm(IMAGE_WIDTH_CM))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER

        table = doc.add_table(rows=1 + len(version["criteria"]), cols=6)
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        fix_widths(table, [7.5] + [1.9] * 5)
        for c, text in zip(table.rows[0].cells, ["Tiêu chí", "1", "2", "3", "4", "5"]):
            add_text_cell(c, text, bold=True, center=c is not table.rows[0].cells[0])
        for crit, row in zip(version["criteria"], table.rows[1:]):
            cells = row.cells
            par = cells[0].paragraphs[0]
            style_run(par.add_run(crit["label"]), 10, bold=True)
            qp = cells[0].add_paragraph()
            style_run(qp.add_run(crit["question"]), 8, italic=True, color=(92, 103, 112))
            for score, c in enumerate(cells[1:], start=1):
                c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
                add_checkbox(c.paragraphs[0], f"{item['code']}|{crit['key']}|{score}")

        if decide:
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(8)
            style_run(p.add_run("Quyết định:  "), bold=True)
            for key, label in DECISIONS:
                add_checkbox(p, f"{item['code']}|decision|{key}", label + "    ")
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(8)
        style_run(p.add_run("Nhận xét. "), bold=True)
        style_run(p.add_run(spec["commentHelp"]), 9, italic=True, color=(92, 103, 112))
        add_box(doc, 3.0)

    doc.add_heading("Góp ý chung", level=1).paragraph_format.page_break_before = True
    for q in spec["closing"]:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(12)
        style_run(p.add_run(q), bold=True)
        add_box(doc, 3.0)
    return doc


def check_spec(spec: dict) -> None:
    """Báo lỗi rõ ràng khi spec thiếu khóa, thiếu tiêu chí hoặc thiết kế, hoặc trùng tên tệp và mã ảnh."""
    missing = [k for k in ("title", "scale", "profile", "closing", "commentHelp", "versions") if k not in spec]
    if missing:
        raise ValueError("form_spec.json thiếu khóa: " + ", ".join(missing))
    bad = [q for q in spec["profile"] if q.get("type") not in ("text", "choice")]
    if bad:
        raise ValueError("profile chỉ hỗ trợ type text hoặc choice, gặp: " + ", ".join(str(q.get("type")) for q in bad))
    names = [slug(v["label"]) for v in spec["versions"]]
    if len(set(names)) != len(names):
        raise ValueError("hai vai có tên tệp trùng nhau, sẽ ghi đè nhau: " + ", ".join(names))
    for v in spec["versions"]:
        if not v.get("criteria") or not v.get("items"):
            raise ValueError(f"vai {v.get('label')} không có tiêu chí hoặc không có thiết kế nào")
        codes = [i["code"] for i in v["items"]]
        if len(set(codes)) != len(codes):
            raise ValueError(f"vai {v['label']} có mã ảnh trùng nhau, thẻ ô tích sẽ không duy nhất")


def write_docx(spec: dict, images_dir: Path, out_dir: Path) -> list[Path]:
    """Ghi mỗi vai một file .docx vào out_dir, trả về danh sách đường dẫn."""
    if spec.get("mode") != "expert":
        raise ValueError("write_docx chỉ dùng cho gói phiếu chuyên gia (form_spec.json có mode=expert)")
    check_spec(spec)
    missing = sorted({i["file"] for v in spec["versions"] for i in v["items"] if not (images_dir / i["file"]).exists()})
    if missing:
        raise FileNotFoundError(f"thiếu ảnh trong {images_dir}: " + ", ".join(missing))
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for v in spec["versions"]:
        path = out_dir / f"Phieu_{slug(v['label'])}.docx"
        build_doc(spec, v, images_dir).save(path)
        paths.append(path)
    return paths


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", default="outputs/review/google_form_EXP-A_expert", help="thư mục gói phiếu chuyên gia")
    args = ap.parse_args()
    pkg = Path(args.package) if Path(args.package).is_absolute() else ROOT / args.package
    spec = json.loads((pkg / "form_spec.json").read_text(encoding="utf-8"))
    for p in write_docx(spec, pkg / "images", pkg / "docx"):
        print(f"Đã ghi {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
