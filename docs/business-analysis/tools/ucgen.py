# -*- coding: utf-8 -*-
"""Sinh sơ đồ Use Case UML 2.5 (SVG để chèn báo cáo + PlantUML để chỉnh sửa) cho AS-IS và TO-BE.

    python ucgen.py <thư mục ra>
"""
import math
import sys
from pathlib import Path
from xml.sax.saxutils import escape

FONT = "Arial, Helvetica, sans-serif"
INK = "#1D2A36"
FILL = {"main": ("#E8F0FA", "#2B5C94"), "incl": ("#F1ECFA", "#5A3E99"), "new": ("#E1F3E4", "#2E7D32"),
        "changed": ("#FFF4D6", "#8A6100")}
A, B, C = 455, 870, 1255          # ba cột ca sử dụng (khe A–B rộng để nhãn «include» tránh chỗ giao)
RX, RY = 124, 34

# --------------------------------------------------------------------------- mô hình
UC = {   # mã: (tên, cột x, y, loại)
    "UC01": ("Tra cứu hiện vật", A, 130, "main"),
    "UC02": ("Xem ý nghĩa hoa văn", B, 130, "main"),
    "UC03": ("Tạo thiết kế áo dài", A, 400, "main"),
    "UC06": ("Tải lên bản chỉnh sửa", A, 600, "main"),
    "UC04": ("Xem lại thiết kế đã tạo", A, 760, "main"),
    "UC05": ("Tải thiết kế có nhãn AI", A, 870, "main"),
    "UC08": ("Kiểm định chất lượng tự động", B, 400, "incl"),
    "UC09": ("Ghi Design Passport", B, 600, "incl"),
    "UC07": ("Kiểm tra quyền sử dụng", B, 800, "incl"),
    "UC10": ("Xử lý cảnh báo chất lượng", C, 130, "main"),
    "UC11": ("Điều phối thẩm định mù", C, 240, "main"),
    "UC12": ("Chấm mù thiết kế", C, 350, "main"),
    "UC14": ("Tra cứu Design Passport", C, 470, "main"),
    "UC17": ("Chạy thử nghiệm có kiểm soát", C, 590, "main"),
    "UC13": ("Xuất bản thiết kế", C, 800, "main"),
    "UC18": ("Giám sát vận hành", C, 920, "main"),
    "UC15": ("Tiếp nhận hiện vật mới", C, 1050, "main"),
    "UC16": ("Cập nhật quyền sử dụng hiện vật", C, 1160, "main"),
}
ACTORS = {  # mã: (tên, x, y, kiểu)  kiểu: person | system
    "DES": ("Nhà thiết kế", 170, 560, "person"),
    "EXP": ("Chuyên gia thẩm định", 1580, 330, "person"),
    "QC": ("QC Officer", 1580, 520, "person"),
    "OPS": ("Người vận hành", 1580, 860, "person"),
    "DATA": ("Người quản lý dữ liệu", 1580, 1110, "person"),
    "GF": ("Google Forms", 1580, 190, "system"),
    "ZALO": ("Zalo", 1580, 985, "system"),
}
ASSOC = [("DES", "UC01"), ("DES", "UC03"), ("DES", "UC06"), ("DES", "UC04"), ("DES", "UC05"),
         ("QC", "UC10"), ("QC", "UC11"), ("QC", "UC14"), ("QC", "UC17"), ("QC", "UC13"),
         ("EXP", "UC12"), ("GF", "UC12"), ("GF", "UC11"),
         ("OPS", "UC18"), ("ZALO", "UC18"), ("DATA", "UC15"), ("DATA", "UC16")]
REL = [("UC03", "UC08", "include"), ("UC03", "UC09", "include"), ("UC03", "UC07", "include"),
       ("UC06", "UC08", "include"), ("UC06", "UC09", "include"),
       ("UC13", "UC07", "include"), ("UC15", "UC07", "include"),
       ("UC02", "UC01", "extend")]
GEN = []


def tobe_model():
    uc = dict(UC)
    act = dict(ACTORS)
    uc["UC05"] = ("Tải thiết kế có nhãn AI và mã Passport", A, 980, "changed")
    uc["UC21"] = ("Theo dõi trạng thái thiết kế", A, 875, "new")
    uc["UC20"] = ("Đề cử thiết kế đi thẩm định", A, 1090, "new")
    uc["UC11"] = ("Theo dõi hàng đợi thẩm định", C, 240, "changed")
    uc["UC12"] = ("Chấm mù trên cổng thẩm định", C, 350, "changed")
    uc["UC16"] = ("Quản lý đề nghị cấp phép", C, 1160, "changed")
    uc["UC19"] = ("Đăng nhập theo vai trò", C, 1275, "new")
    del act["GF"]
    act["OWN"] = ("Chủ sở hữu ảnh", 150, 1160, "person")
    act["STAFF"] = ("Nhân sự nội bộ", 1720, 1275, "person")
    assoc = [a for a in ASSOC if "GF" not in a] + [("DES", "UC20"), ("DES", "UC21"), ("OWN", "UC16"),
                                                   ("STAFF", "UC19")]
    rel = REL + [("UC21", "UC04", "extend")]
    gen = [("EXP", "STAFF"), ("QC", "STAFF"), ("OPS", "STAFF"), ("DATA", "STAFF")]
    return uc, act, assoc, rel, gen


# --------------------------------------------------------------------------- vẽ SVG
def wrap(text, width=24):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    lines.append(cur)
    return lines


def edge(cx, cy, tx, ty, rx=RX, ry=RY):
    """Giao điểm của tia từ tâm elip (cx, cy) tới (tx, ty) với viền elip."""
    dx, dy = tx - cx, ty - cy
    if dx == 0 and dy == 0:
        return cx, cy
    t = 1 / math.sqrt((dx / rx) ** 2 + (dy / ry) ** 2)
    return cx + dx * t, cy + dy * t


def seg_rect(p, q, r, steps=60):
    """Đoạn p–q có đi qua hình chữ nhật r = (x, y, w, h) không (lấy mẫu dọc đoạn)."""
    x, y, w, h = r
    for i in range(steps + 1):
        t = i / steps
        px, py = p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t
        if x <= px <= x + w and y <= py <= y + h:
            return True
    return False


def rect_hit(a, b):
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


def actor_anchor(a, tx, ty):
    name, x, y, kind = a
    if kind == "system":
        return (x - 95 if tx < x else x + 95), y
    return (x + 22 if tx > x else x - 22), y - 8


def svg(model, title, subtitle):
    uc, act, assoc, rel, gen = model
    DY = 10
    uc = {k: (n, x, y + DY, t) for k, (n, x, y, t) in uc.items()}
    act = {k: (n, x, y + DY, t) for k, (n, x, y, t) in act.items()}
    W = 1860 if any(k == "STAFF" for k in act) else 1760
    H = max(v[2] for v in uc.values()) + 172
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="{FONT}" font-size="15">',
         '<defs><marker id="open" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="12" markerHeight="12" orient="auto">'
         f'<path d="M0,0 L12,6 L0,12" fill="none" stroke="{INK}" stroke-width="1.6"/></marker>'
         '<marker id="tri" viewBox="0 0 14 14" refX="13" refY="7" markerWidth="16" markerHeight="16" orient="auto">'
         f'<path d="M0,0 L14,7 L0,14 z" fill="#fff" stroke="{INK}" stroke-width="1.3"/></marker></defs>',
         '<rect width="100%" height="100%" fill="#fff"/>',
         f'<text x="{W/2}" y="30" text-anchor="middle" font-size="20" font-weight="700" fill="{INK}">{escape(title)}</text>',
         f'<rect x="300" y="52" width="1100" height="{H - 90}" rx="8" fill="none" stroke="{INK}" stroke-width="1.8"/>',
         f'<text data-k="title" x="316" y="76" font-weight="700" fill="{INK}">Nền tảng Tái Sinh Di Sản Số</text>']
    # liên kết actor – ca sử dụng
    segs = []                      # (p, q, khoá) của mọi đường thẳng, để tránh khi đặt nhãn
    for a, u in assoc:
        _, ux, uy, _k = uc[u]
        ax, ay = actor_anchor(act[a], ux, uy)
        ex, ey = (ux - RX, uy) if ax < ux else (ux + RX, uy)   # nối vào điểm cạnh elip phía actor: không cắt elip khác
        segs.append(((ax, ay), (ex, ey), f"assoc:{a}:{u}"))
        o.append(f'<line data-k="assoc" data-s="{a}" data-t="{u}" x1="{ax:.0f}" y1="{ay:.0f}" x2="{ex:.0f}" y2="{ey:.0f}" '
                 f'stroke="{INK}" stroke-width="1.3"/>')
    rel_lines = []
    for s_, t, kind in rel:
        _, sx, sy, _ = uc[s_]
        _, tx, ty, _ = uc[t]
        x1, y1 = edge(sx, sy, tx, ty)
        x2, y2 = edge(tx, ty, sx, sy)
        rel_lines.append((s_, t, kind, (x1, y1), (x2, y2)))
        segs.append(((x1, y1), (x2, y2), f"rel:{s_}:{t}"))
    # include / extend
    placed = []
    for s_, t, kind, p1, p2 in rel_lines:
        o.append(f'<line data-k="rel" data-s="{s_}" data-t="{t}" x1="{p1[0]:.0f}" y1="{p1[1]:.0f}" x2="{p2[0]:.0f}" y2="{p2[1]:.0f}" '
                 f'stroke="{INK}" stroke-width="1.3" stroke-dasharray="7 5" marker-end="url(#open)"/>')
        lbl = "«include»" if kind == "include" else "«extend»"
        best = None
        flat = abs(p2[1] - p1[1]) < 2               # đường nằm ngang: được phép đặt nhãn ngay trên hoặc dưới đường
        cands = [(tt, 0) for tt in (0.5, 0.42, 0.58, 0.34, 0.66, 0.27, 0.73)]
        if flat:
            cands += [(tt, dy) for dy in (-17, 17) for tt in (0.5, 0.4, 0.6, 0.3, 0.7)]
        for tt, dy in cands:
            mx, my = p1[0] + (p2[0] - p1[0]) * tt, p1[1] + (p2[1] - p1[1]) * tt + dy
            r = (mx - 38, my - 12, 76, 22)
            far = (mx - 50, my - 22, 100, 44)       # chừa khoảng cách với đường khác để nhãn rõ thuộc đường nào
            others = [(a_, b_) for a_, b_, key in segs if key != f"rel:{s_}:{t}"]
            bad = 100 * sum(1 for a_, b_ in others if seg_rect(a_, b_, r)) + sum(1 for a_, b_ in others if seg_rect(a_, b_, far))
            bad += 100 * sum(1 for q in placed if rect_hit(r, q))
            bad += 100 * sum(1 for (_, ex_, ey_, _) in uc.values() if abs(mx - ex_) < RX + 30 and abs(my - ey_) < RY + 6)
            if best is None or bad < best[0]:
                best = (bad, mx, my, r)
            if bad == 0:
                break
        _, mx, my, r = best
        placed.append(r)
        o.append(f'<rect data-k="rel-bg" x="{mx - 36:.0f}" y="{my - 11:.0f}" width="72" height="20" fill="#fff"/>'
                 f'<text data-k="rel-label" data-s="{s_}" data-t="{t}" x="{mx:.0f}" y="{my + 4:.0f}" text-anchor="middle" '
                 f'font-size="13" fill="{INK}">{lbl}</text>')
    # tổng quát hoá actor: một trục chung dẫn tới actor cha
    if gen:
        parent = act[gen[0][1]]
        px, py = parent[1], parent[2]
        trunk = px
        ys = [act[c][2] - 8 for c, _ in gen]
        for c, _ in gen:
            cx, cy = act[c][1] + 22, act[c][2] - 8
            o.append(f'<line x1="{cx}" y1="{cy}" x2="{trunk}" y2="{cy}" stroke="{INK}" stroke-width="1.3"/>')
        o.append(f'<line x1="{trunk}" y1="{min(ys)}" x2="{trunk}" y2="{py - 58}" stroke="{INK}" stroke-width="1.3" marker-end="url(#tri)"/>')
    # ca sử dụng
    for code, (name, x, y, k) in uc.items():
        fill, stroke = FILL[k]
        dash = ' stroke-dasharray="6 4"' if k == "new" else ""
        o.append(f'<ellipse data-o="{code}" cx="{x}" cy="{y}" rx="{RX}" ry="{RY}" fill="{fill}" stroke="{stroke}" stroke-width="1.6"{dash}/>')
        lines = [code] + wrap(name, 26)
        y0 = y - (len(lines) - 1) * 9
        for i, t in enumerate(lines):
            weight = ' font-weight="700"' if i == 0 else ""
            o.append(f'<text data-k="uc" data-o="{code}" x="{x}" y="{y0 + i * 18 + 5:.0f}" text-anchor="middle" font-size="{13 if i == 0 else 14}"'
                     f'{weight} fill="{stroke}">{escape(t)}</text>')
    # actor
    for code, (name, x, y, kind) in act.items():
        if kind == "system":
            o.append(f'<rect x="{x - 95}" y="{y - 30}" width="190" height="60" rx="4" fill="#F2F2F2" stroke="#5F6368" stroke-width="1.4"/>'
                     f'<text x="{x}" y="{y - 8}" text-anchor="middle" font-size="12" fill="#5F6368">«hệ thống ngoài»</text>'
                     f'<text x="{x}" y="{y + 14}" text-anchor="middle" font-size="14" fill="{INK}">{escape(name)}</text>')
            continue
        o.append(f'<g stroke="{INK}" stroke-width="2" fill="none"><circle cx="{x}" cy="{y - 48}" r="11" fill="#fff"/>'
                 f'<line x1="{x}" y1="{y - 37}" x2="{x}" y2="{y}"/><line x1="{x - 20}" y1="{y - 24}" x2="{x + 20}" y2="{y - 24}"/>'
                 f'<line x1="{x}" y1="{y}" x2="{x - 16}" y2="{y + 26}"/><line x1="{x}" y1="{y}" x2="{x + 16}" y2="{y + 26}"/></g>')
        lines = wrap(name, 18)
        if code == "DES":          # nhiều đường toả xuống dưới: nhãn đặt bên trái để không bị đường cắt
            for i, t in enumerate(lines):
                o.append(f'<text data-k="actor" data-o="{code}" x="{x - 28}" y="{y - 14 + i * 17}" text-anchor="end" '
                         f'fill="{INK}">{escape(t)}</text>')
        else:
            for i, t in enumerate(lines):
                o.append(f'<text data-k="actor" data-o="{code}" x="{x}" y="{y + 46 + i * 17}" text-anchor="middle" '
                         f'fill="{INK}">{escape(t)}</text>')
    # chú giải
    ly = H - 18
    items = [("main", "Ca sử dụng"), ("incl", "Ca được include (luôn chạy kèm)")]
    if gen:
        items += [("changed", "Ca thay đổi so với AS-IS"), ("new", "Ca mới đề xuất")]
    x = 320
    for k, t in items:
        fill, stroke = FILL[k]
        o.append(f'<ellipse cx="{x + 18}" cy="{ly}" rx="18" ry="9" fill="{fill}" stroke="{stroke}"/>'
                 f'<text x="{x + 44}" y="{ly + 5}" font-size="13" fill="{INK}">{escape(t)}</text>')
        x += 60 + len(t) * 7
    o.append("</svg>")
    return "\n".join(o)


def puml(model, title):
    uc, act, assoc, rel, gen = model
    p = ["@startuml", f"title {title}", "left to right direction", "skinparam packageStyle rectangle",
         "skinparam usecase { BackgroundColor #E8F0FA\n BorderColor #2B5C94 }"]
    for code, (name, x, y, kind) in act.items():
        if kind == "system":
            p.append(f'actor "{name}" as {code} <<hệ thống ngoài>>')
        else:
            p.append(f'actor "{name}" as {code}')
    p.append('rectangle "Nền tảng Tái Sinh Di Sản Số" {')
    for code, (name, x, y, k) in uc.items():
        tag = {"new": " <<mới>>", "changed": " <<thay đổi>>", "incl": "", "main": ""}[k]
        p.append(f'  usecase "{code} – {name}" as {code}{tag}')
    p.append("}")
    for a, u in assoc:
        p.append(f"{a} -- {u}")
    for s, t, kind in rel:
        p.append(f"{s} ..> {t} : <<{kind}>>")
    for c, par in gen:
        p.append(f"{c} --|> {par}")
    p.append("@enduml")
    return "\n".join(p) + "\n"


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    asis = (UC, ACTORS, ASSOC, REL, GEN)
    tobe = tobe_model()
    for name, model, title, sub in (
        ("UC-AS-IS_use-case", asis, "Sơ đồ Use Case AS-IS — Tái Sinh Di Sản Số",
         "Hiện trạng theo mã nguồn (24/11/2026): 18 ca sử dụng, 5 tác nhân người, 2 hệ thống ngoài"),
        ("UC-TO-BE_use-case", tobe, "Sơ đồ Use Case TO-BE — Tái Sinh Di Sản Số",
         "Đề xuất tối ưu: 21 ca sử dụng; ca mới nét đứt màu xanh lá, ca thay đổi màu vàng"),
    ):
        (out / f"{name}.svg").write_text(svg(model, title, sub), encoding="utf-8")
        (out / f"{name}.puml").write_text(puml(model, title), encoding="utf-8")
    print("ok")
