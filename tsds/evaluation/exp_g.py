# -*- coding: utf-8 -*-
"""Thí nghiệm EXP-G: bốn cách tạo ô hoa văn từ mảng phẳng của hiện vật.

"Ô hoa văn" là ảnh nhỏ mà `garment.apply` lát liền lên áo. Cả bốn mức cùng dùng áo LoRA, cùng bố cục,
cùng polish có mặt nạ; chỉ khác cách tạo ô hoa văn:

  sd_controlnet  cách hiện tại: Canny của mảng phẳng đưa vào ControlNet, Stable Diffusion vẽ lại hoàn toàn
  paste_direct   mốc dán nguyên: cắt một hình chữ nhật lớn nhất nằm trọn trong mảng, làm liền mạch, KHÔNG vẽ lại
  img2img_low    lấy ô của paste_direct rồi vẽ lại nhẹ bằng img2img (độ nhiễu thấp), giữ màu và bố cục
  elements_sam   dán một phần tử đã cắt bằng SAM (data/elements/), xếp so le thành ô lát
  elements_clip  như elements_sam nhưng chọn phần tử nguyên vẹn và khớp mô tả hiện vật nhất (pick_main_element)
  elements_boost như elements_clip nhưng kéo mực ra xa màu nền (boost_ink) để bớt nhạt
  paste_boost    như paste_direct nhưng kéo giãn tương phản và sắc xanh của mực trước khi ghép (sửa lỗi in mờ)

Mã này nằm riêng trong tsds/evaluation/, không sửa pipeline chính. Chạy:
    uv run python -m tsds.evaluation.exp_g run
"""
from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

SPEC = ROOT / "tsds" / "evaluation" / "experiments" / "EXP-G_pattern_method.json"
PANELS_DIR = ROOT / "data" / "heritage" / "panels"
LEVELS = ("sd_controlnet", "paste_direct", "img2img_low", "elements_sam", "paste_boost", "elements_clip",
          "elements_boost")
TILE_MAX = 1024          # cạnh dài tối đa của ô dán nguyên (ô sẽ bị thu nhỏ khi lát lên áo nên không cần lớn hơn)
IMG2IMG_SIDE = 512       # cạnh dài của ô đưa vào img2img (độ phân giải gốc của SD 1.5)
EDGE_MARGIN = 0.03       # lùi vào trong hình chữ nhật tối đa 3% mỗi phía để tránh mép rách của mảng


# ------------------------------------------------------------ cắt ô từ mảng ----

def largest_rect(mask: np.ndarray) -> tuple[int, int, int, int]:
    """Hình chữ nhật diện tích lớn nhất chỉ gồm điểm 1 của mặt nạ. Trả về (x0, y0, x1, y1), x1 và y1 là biên mở.

    Dùng thuật toán biểu đồ cột: mỗi hàng tính chiều cao cột liên tiếp rồi tìm hình chữ nhật lớn nhất dưới biểu đồ.
    Mặt nạ rỗng thì trả về (0, 0, 0, 0).
    """
    h, w = mask.shape
    heights = np.zeros(w, np.int32)
    best, box = 0, (0, 0, 0, 0)
    for y in range(h):
        heights = np.where(mask[y] > 0, heights + 1, 0)
        stack: list[int] = []                       # chỉ số các cột có chiều cao tăng dần
        for x in range(w + 1):
            cur = int(heights[x]) if x < w else 0
            start = x
            while stack and int(heights[stack[-1]]) >= cur:
                top = stack.pop()
                left = stack[-1] + 1 if stack else 0
                area = int(heights[top]) * (x - left)
                if area > best:
                    best, box = area, (left, y - int(heights[top]) + 1, x, y + 1)
                start = left
            stack.append(x if x < w else start)
    return box


def crop_inscribed(panel: Image.Image, tile_max: int = TILE_MAX) -> Image.Image:
    """Cắt hình chữ nhật lớn nhất nằm trọn trong vùng có nội dung của mảng (kênh alpha), thu về cạnh dài tile_max."""
    rgba = np.asarray(panel.convert("RGBA"))
    valid = (rgba[:, :, 3] > 10).astype(np.uint8)
    valid = cv2.erode(valid, np.ones((9, 9), np.uint8))          # bỏ dải mép rách
    s = 8                                                         # tính trên bản thu nhỏ 8 lần cho nhanh
    small = cv2.resize(valid, (valid.shape[1] // s, valid.shape[0] // s), interpolation=cv2.INTER_AREA)
    x0, y0, x1, y1 = largest_rect((small > 0.99).astype(np.uint8))
    if x1 <= x0 or y1 <= y0:
        raise ValueError("Mảng không có hình chữ nhật hợp lệ để cắt")
    x0, y0, x1, y1 = x0 * s, y0 * s, x1 * s, y1 * s
    mx, my = int((x1 - x0) * EDGE_MARGIN), int((y1 - y0) * EDGE_MARGIN)
    crop = panel.convert("RGB").crop((x0 + mx, y0 + my, x1 - mx, y1 - my))
    k = tile_max / max(crop.size)
    if k < 1:
        crop = crop.resize((max(1, round(crop.width * k)), max(1, round(crop.height * k))), Image.LANCZOS)
    return crop


BLEND_BAND = 0.15   # bề rộng dải hòa mép, tính theo tỉ lệ cạnh ô, mỗi phía


def make_seamless(img: Image.Image, band: float = BLEND_BAND) -> Image.Image:
    """Làm ô liền mạch khi lát: ở dải sát mép, hòa ảnh với bản dịch nửa ô; phần giữa giữ nguyên pixel gốc.

    Trọng số w đi từ 0 ở mép lên 1 sau `band` (tỉ lệ cạnh ô). Ở mép kết quả lấy từ bản dịch, mà mép trái và mép phải
    của bản dịch là hai cột kề nhau của ảnh gốc, nên hai mép nối liền. Chỉ dải mép có bóng mờ (hai nét chồng nhau);
    phần giữa, chiếm (1 - 2*band)^2 diện tích, là pixel gốc. Không dùng lát gương vì gương gây đối xứng giả.
    """
    if not 0 < band <= 0.5:
        raise ValueError("band phải trong (0, 0,5]")
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    h, w = a.shape[:2]
    shifted = np.roll(a, (h // 2, w // 2), axis=(0, 1))

    def ramp(n: int) -> np.ndarray:
        d = np.minimum(np.arange(n) + 0.5, n - np.arange(n) - 0.5) / (band * n)     # khoảng cách tới mép, chuẩn hóa
        t = np.clip(d, 0, 1)
        return t * t * (3 - 2 * t)                                                    # smoothstep: 0 ở mép, 1 trong ruột

    wgt = (ramp(h)[:, None] * ramp(w)[None, :])[:, :, None]
    return Image.fromarray(np.clip(a * wgt + shifted * (1 - wgt), 0, 255).astype(np.uint8))


# ------------------------------------------------------------ sửa in mờ ----

def boost_ink(img: Image.Image, ground: tuple[int, int, int], target_dl: float = 60.0,
              target_chroma: float = 45.0, kmax_l: float = 3.0, kmax_c: float = 2.0) -> Image.Image:
    """Kéo mực ra xa màu nền để mực không bị in mờ trên áo.

    Vì sao mờ: `garment.apply` chỉ in điểm có sắc độ từ 16 đến 34 hoặc đủ tối (L dưới 60). Mảng phẳng cắt từ ảnh bình
    có sắc độ thấp (p90 chỉ 11 đến 30, ô do SD sinh là 28 đến 62) nên phần lớn nét bị in nhạt hoặc bỏ.

    Cách làm trong LAB, neo tại màu nền để nền không đổi:
      1. Hệ số kl kéo khoảng cách (độ sáng và sắc) tới màu nền: phân vị 98 của khoảng cách được đưa lên target_dl, kl trong [1, kmax_l].
      2. Hệ số kc kéo riêng sắc độ: phân vị 95 của sắc độ tới target_chroma, kc trong [1, kmax_c]. Chỉ áp cho điểm
         nghiêng về xanh (b < 0, trọng số tăng dần tới b = -10), để không phóng đại vết ố vàng của men.
    Hệ số bằng 1 khi ảnh đã đủ tương phản, nên hiện vật rõ nét (LR3D_50, LR3D_61) gần như không đổi.
    """
    rgb = np.asarray(img.convert("RGB"), np.float32) / 255
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    g = cv2.cvtColor(np.array([[ground]], np.float32) / 255, cv2.COLOR_RGB2LAB)[0, 0]
    d = lab - g
    kl = float(np.clip(target_dl / max(np.percentile(np.sqrt((d ** 2).sum(-1)), 98), 1e-3), 1.0, kmax_l))
    kc = float(np.clip(target_chroma / max(np.percentile(np.hypot(d[..., 1], d[..., 2]), 95), 1e-3), 1.0, kmax_c))
    d = d * kl
    w = np.clip(-d[..., 2] / 10.0, 0, 1)                      # chỉ kéo sắc điểm nghiêng về xanh
    d[..., 1:] *= (1 + (kc - 1) * w)[..., None]
    out = g + d
    out[..., 0] = np.clip(out[..., 0], 0, 100)
    out[..., 1:] = np.clip(out[..., 1:], -127, 127)
    rgb_out = np.clip(cv2.cvtColor(out.astype(np.float32), cv2.COLOR_LAB2RGB), 0, 1)
    return Image.fromarray((rgb_out * 255).round().astype(np.uint8))


# ----------------------------------------------------------- phần tử SAM ----

def ground_color(panel: Image.Image) -> tuple[int, int, int]:
    """Màu nền men: trung vị của 20% điểm sáng nhất trong vùng có nội dung của mảng."""
    rgba = np.asarray(panel.convert("RGBA"))
    px = rgba[rgba[:, :, 3] > 10][:, :3]
    lum = px.mean(axis=1)
    top = px[lum >= np.percentile(lum, 80)]
    return tuple(int(v) for v in np.median(top, axis=0))


def tile_from_element(element: Image.Image, ground: tuple[int, int, int], fill: float = 0.45) -> Image.Image:
    """Xếp một phần tử RGBA thành ô lát so le (nửa bước): một bản ở giữa, các bản còn lại ở bốn góc.

    Cạnh ô t = cạnh dài phần tử / fill, với fill ≤ 0,5 thì bản giữa và bản ở góc không chồng nhau (tâm cách nhau t/2).
    Ô liền mạch theo cấu trúc, không cần hòa mép. Phần tử bị thu nhỏ để cạnh dài tối đa bằng TILE_MAX*fill.
    """
    if not 0 < fill <= 0.5:
        raise ValueError("fill phải trong (0, 0,5] để các bản không chồng nhau")
    el = element.convert("RGBA")
    box = el.getchannel("A").point(lambda v: 255 if v > 10 else 0).getbbox()
    if box is None:
        raise ValueError("Phần tử không có điểm nào đục")
    el = el.crop(box)
    k = TILE_MAX * fill / max(el.size)
    if k < 1:
        el = el.resize((max(1, round(el.width * k)), max(1, round(el.height * k))), Image.LANCZOS)
    t = int(round(max(el.size) / fill))
    # Vẽ lên lưới 3x3 ô: bản giữa tại (t/2, t/2) và bản góc tại (0, 0), lặp ở mọi ô; lấy ô giữa của lưới
    # nên phần phần tử tràn qua mép ô tự nối sang mép đối diện (ô lát liền mạch theo cấu trúc).
    grid = Image.new("RGBA", (3 * t, 3 * t), (0, 0, 0, 0))
    for ox in (0, t, 2 * t):
        for oy in (0, t, 2 * t):
            for cx, cy in ((t // 2, t // 2), (0, 0)):
                _paste_clipped(grid, el, ox + cx - el.width // 2, oy + cy - el.height // 2)
    layer = grid.crop((t, t, 2 * t, 2 * t))
    canvas = Image.new("RGB", (t, t), ground)
    canvas.paste(layer.convert("RGB"), (0, 0), layer.getchannel("A"))
    return canvas


def _paste_clipped(dst: Image.Image, src: Image.Image, x: int, y: int) -> None:
    """Dán src (RGBA) lên dst tại (x, y), cho phép tràn ra ngoài khung (phần tràn bị cắt bỏ)."""
    dst.alpha_composite(src, (max(x, 0), max(y, 0)),
                        (max(-x, 0), max(-y, 0), min(src.width, dst.width - x), min(src.height, dst.height - y)))


# --------------------------------------------------- chọn phần tử chính ----

ELEM_MIN_SIDE = 200      # cạnh ngắn tối thiểu (pixel): nhỏ hơn thì quá mờ khi đưa lên áo
ELEM_MAX_ASPECT = 2.6    # tỉ lệ cạnh dài / cạnh ngắn tối đa: dải quá dài làm ô lát gần như trống
ELEM_MIN_FILL = 0.30     # độ lấp đầy tối thiểu của hộp bao (phần đục / diện tích hộp): thấp là hình rời rạc, đứt đoạn
ELEM_SIZE_REF = 400      # phần tử có cạnh ngắn dưới mức này bị phạt nhẹ
ELEM_SIZE_EXP = 0.25     # số mũ của hệ số phạt kích thước: (cạnh ngắn / ELEM_SIZE_REF) ** ELEM_SIZE_EXP


def element_score(clip: float, size_wh: tuple[int, int]) -> float:
    """Điểm một phần tử = độ khớp CLIP với mô tả hiện vật, nhân hệ số phạt nhẹ cho phần tử nhỏ (tối đa 1)."""
    return clip * min(1.0, min(size_wh) / ELEM_SIZE_REF) ** ELEM_SIZE_EXP


def rank_elements(cands: list[dict]) -> list[dict]:
    """Xếp hạng phần tử ứng viên, điểm cao đứng trước. Mỗi ứng viên có element_id, size_wh, fill và clip.

    Lọc theo hình dạng: cạnh ngắn >= ELEM_MIN_SIDE, tỉ lệ cạnh <= ELEM_MAX_ASPECT, fill >= ELEM_MIN_FILL.
    Không ứng viên nào qua bộ lọc thì xếp tất cả (không để hiện vật không có phần tử).
    Quy tắc này chọn phần tử NGUYÊN VẸN và KHỚP MÔ TẢ, nhưng không biết đâu là hình chính khi mô tả có nhiều thành phần
    (ví dụ "rồng và mây" có thể ra mây). Hòa điểm thì theo element_id để kết quả tất định.
    """
    ok = [c for c in cands if min(c["size_wh"]) >= ELEM_MIN_SIDE
          and max(c["size_wh"]) / min(c["size_wh"]) <= ELEM_MAX_ASPECT and c["fill"] >= ELEM_MIN_FILL]
    pool = ok or cands
    return sorted(pool, key=lambda c: (-element_score(c["clip"], c["size_wh"]), c["element_id"]))


def element_fill(element: Image.Image) -> float:
    """Độ lấp đầy: tỉ lệ điểm đục (alpha > 10) trong hộp bao của phần tử."""
    a = np.asarray(element.convert("RGBA").getchannel("A")) > 10
    if not a.any():
        return 0.0
    return float(a[np.ix_(a.any(1), a.any(0))].mean())


_CLIP: dict = {}


def _clip():
    """Nạp CLIP ViT-B/32 một lần (chạy trên CPU, chỉ vài chục ảnh nhỏ)."""
    if not _CLIP:
        from transformers import CLIPModel, CLIPProcessor        # noqa: PLC0415
        _CLIP["m"] = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").eval()
        _CLIP["p"] = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    return _CLIP["m"], _CLIP["p"]


def pick_main_element(heritage_id: str) -> dict:
    """Chọn một phần tử cho hiện vật: CLIP chấm độ khớp giữa ảnh phần tử (đặt trên màu nền men) và mô tả hiện vật.

    Mô tả = name_en và base_description trong data/prompt_terms.json. Trả về bản ghi phần tử trong
    data/elements/index.json, thêm các khóa clip, fill, score. Kết quả tất định (CLIP không ngẫu nhiên).
    """
    import json as _json                                         # noqa: PLC0415
    import torch                                                 # noqa: PLC0415
    import torch.nn.functional as F                              # noqa: PLC0415
    from tsds.generation.pattern import element_library as EL, pattern        # noqa: PLC0415
    obj = EL.object_of(heritage_id)
    recs = [r for r in _json.loads(EL.INDEX_PATH.read_text(encoding="utf-8"))
            if r["object_id"] == obj and (ROOT / r["file"]).is_file()]
    if not recs:
        raise ValueError(f"Kho phần tử không có phần tử cho {heritage_id}")
    m, proc = _clip()
    t = pattern.TERMS[heritage_id]
    ground = ground_color(Image.open(PANELS_DIR / f"{heritage_id}.png"))
    with torch.no_grad():
        te = F.normalize(m.text_projection(m.text_model(**proc(
            text=[f"{t['name_en']}, {t['base_description']}"], return_tensors="pt", padding=True, truncation=True)
        ).pooler_output), dim=-1)[0]
        cands = []
        for r in recs:
            el = Image.open(ROOT / r["file"]).convert("RGBA")
            bg = Image.new("RGB", el.size, ground)
            bg.paste(el.convert("RGB"), mask=el.getchannel("A"))
            ie = F.normalize(m.visual_projection(m.vision_model(**proc(images=bg, return_tensors="pt")).pooler_output),
                             dim=-1)[0]
            cands.append({**r, "clip": float(ie @ te), "fill": element_fill(el)})
    best = rank_elements(cands)[0]
    return {**best, "score": element_score(best["clip"], best["size_wh"])}


# ------------------------------------------------------------- độ trung thành ----

def sift_inlier_ratio(pattern: Image.Image, panel: Image.Image, max_side: int = 1024) -> float:
    """Tỉ lệ điểm đặc trưng SIFT của ô hoa văn khớp được với mảng gốc (sau khi lọc bằng RANSAC).

    SIFT tìm điểm đặc trưng cục bộ, không đổi theo tỉ lệ và xoay. RANSAC giữ lại các cặp khớp cùng một phép
    đồng dạng (dời, xoay, đổi tỉ lệ). Gần 1: ô là bản sao của mảng. Gần 0: ô là nét vẽ mới, không còn pixel nào kế thừa.
    Chỉ đo kế thừa pixel, không đo "trông có giống không".
    """
    def gray(im: Image.Image) -> np.ndarray:
        g = np.asarray(im.convert("L"))
        k = max_side / max(g.shape)
        return cv2.resize(g, None, fx=k, fy=k, interpolation=cv2.INTER_AREA) if k < 1 else g

    sift = cv2.SIFT_create()
    kp_p, des_p = sift.detectAndCompute(gray(pattern), None)
    kp_s, des_s = sift.detectAndCompute(gray(panel), None)
    if des_p is None or des_s is None or len(kp_p) < 4 or len(kp_s) < 4:
        return 0.0
    pairs = cv2.BFMatcher().knnMatch(des_p, des_s, k=2)
    good = [m for m, n in (p for p in pairs if len(p) == 2) if m.distance < 0.75 * n.distance]
    if len(good) < 4:
        return 0.0
    src = np.float32([kp_p[m.queryIdx].pt for m in good])
    dst = np.float32([kp_s[m.trainIdx].pt for m in good])
    _, inl = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC, ransacReprojThreshold=4.0)
    return 0.0 if inl is None else float(inl.sum()) / len(kp_p)


# ------------------------------------------------------------------ chạy ----

@contextmanager
def circular_padding(pipe):
    """Tạm bật padding vòng cho UNet và VAE của pipeline để ảnh sinh ra liền mạch, rồi trả về như cũ.

    Pipeline img2img này dùng chung cho polish, mà polish cần padding thường, nên phải trả lại.
    """
    import torch                                                # noqa: PLC0415
    convs = [m for net in (pipe.unet, pipe.vae) for m in net.modules() if isinstance(m, torch.nn.Conv2d)]
    old = [m.padding_mode for m in convs]
    for m in convs:
        m.padding_mode = "circular"
    try:
        yield
    finally:
        for m, mode in zip(convs, old):
            m.padding_mode = mode


def img2img_tile(tile: Image.Image, prompt: str, negative: str, strength: float, seed: int) -> Image.Image:
    """Vẽ lại nhẹ một ô đã liền mạch bằng img2img (độ nhiễu strength), giữ nguyên kích thước và tính liền mạch."""
    import torch                                                # noqa: PLC0415
    from tsds.generation.garment import garment                              # noqa: PLC0415
    k = IMG2IMG_SIDE / max(tile.size)
    w, h = (max(64, int(round(tile.width * k / 8)) * 8), max(64, int(round(tile.height * k / 8)) * 8))
    pipe = garment._img2img_pipe()
    with circular_padding(pipe):
        out = pipe(prompt=prompt, negative_prompt=negative, image=tile.resize((w, h), Image.LANCZOS),
                   strength=strength, num_inference_steps=25, guidance_scale=7.5,
                   generator=torch.Generator("cuda").manual_seed(seed)).images[0]
    return out


def build_pattern(method: str, heritage_id: str, *, gen, prepared: dict, seed: int, weight: float,
                  img2img_strength: float) -> tuple[Image.Image, dict]:
    """Tạo ô hoa văn theo một trong bốn cách. Trả về (ảnh, thông tin thêm)."""
    from tsds.generation.pattern import element_library, pattern                # noqa: PLC0415
    from tsds.generation.prompt_template import NEG_PATTERN, assemble_pattern   # noqa: PLC0415
    panel = Image.open(PANELS_DIR / f"{heritage_id}.png")
    if method == "sd_controlnet":
        res = pattern.generate_custom(gen, heritage_id, weight, seed, "", prepared=prepared)
        return res["image"], {"duration_s": res["duration_s"]}
    if method == "paste_direct":
        return make_seamless(crop_inscribed(panel)), {}
    if method in ("elements_clip", "elements_boost"):
        rec = pick_main_element(heritage_id)
        ground = ground_color(panel)
        tile = tile_from_element(Image.open(ROOT / rec["file"]), ground)
        if method == "elements_boost":
            tile = boost_ink(tile, ground)      # cùng hàm với paste_boost: kéo mực ra xa màu nền
        return tile, {"element_id": rec["element_id"]}
    if method == "paste_boost":
        return boost_ink(make_seamless(crop_inscribed(panel)), ground_color(panel)), {}
    if method == "img2img_low":
        t = pattern.TERMS[heritage_id]
        prompt = assemble_pattern(t["name_en"], t["base_description"], "")
        base = make_seamless(crop_inscribed(panel, IMG2IMG_SIDE))
        return img2img_tile(base, prompt, NEG_PATTERN, img2img_strength, seed), {}
    if method == "elements_sam":
        picked = element_library.pick(heritage_id, 1)
        if not picked:
            raise ValueError(f"Kho phần tử không có phần tử cho {heritage_id}")
        el = Image.open(ROOT / picked[0]["file"])
        return tile_from_element(el, ground_color(panel)), {"element_id": picked[0]["element_id"]}
    raise ValueError(f"Cách tạo ô không hợp lệ: {method!r}")


def run(spec: dict, rows: list[dict], out_dir: Path, keep: list[dict] | None = None) -> list[dict]:  # pragma: no cover - cần GPU
    """Chạy kế hoạch trên GPU. Cấu trúc giống experiment.run_gpu, chỉ khác bước tạo ô hoa văn.

    keep: kết quả đã có của các mức không chạy lại; được giữ nguyên ở đầu results.csv."""
    from tsds.evaluation import experiment as E                       # noqa: PLC0415
    from tsds.generation.pattern import controlnet as cn
    from tsds.generation.garment import garment             # noqa: PLC0415
    from tsds.generation.stable_diffusion import Generator            # noqa: PLC0415
    from tsds.provenance.hashing import sha256_file                   # noqa: PLC0415
    from tsds.quality.assess import assess_design                     # noqa: PLC0415
    from tsds.core.pattern_lock import pattern_lock

    img_dir = out_dir / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    garments = E.pregenerate_garments(E.lora_garment_seeds(rows), out_dir)
    need_sd = any(r["iv_level"] == "sd_controlnet" for r in rows)
    gen = Generator() if need_sd else None
    results, prepared = list(keep or []), {}
    try:
        for r in rows:
            try:
                hid, method = r["heritage_id"], r["iv_level"]
                seed = int(r["cfg.seed"])
                g = garments[seed]
                if not g["ok"]:
                    results.append({**r, "status": "garment_failed", "garment_error": g["error"]})
                    continue
                tpl_path, region = g["info"]["path"], g["info"]["mask"]
                # Ảnh tham chiếu và Canny luôn lấy từ mảng phẳng để cả bốn mức đo trên cùng một tham chiếu
                prep = E.source_prepared(prepared, hid, "panel")
                pat, extra = build_pattern(method, hid, gen=gen, prepared=prep, seed=seed,
                                           weight=float(r["cfg.controlnet_weight"]),
                                           img2img_strength=float(r["cfg.img2img_strength"]))
                key = r["run_key"].replace("|", "__").replace("=", "-")
                pat_path = img_dir / f"{key}__pattern.png"
                pat.save(pat_path)
                raw = garment.apply(pat, layout=r["cfg.layout"], template_path=tpl_path, garment_region=region)
                raw_path = img_dir / f"{key}__raw.png"
                raw.save(raw_path)
                kind, strength, lock = E.parse_finish(r["cfg.stage2_finish"])
                if kind != "masked":
                    raise ValueError("exp_g chỉ hỗ trợ stage2_finish dạng masked_*")
                final = garment.polish_masked(raw, strength=strength, seed=seed, mask=region)
                if lock:
                    tpl = Image.open(tpl_path).convert("RGB")
                    lm = garment._layout_mask(tpl, garment.get_layout(r["cfg.layout"]), region)
                    locked, _ = pattern_lock(np.asarray(raw), np.asarray(final.convert("RGB")), lm)
                    final = Image.fromarray(locked)
                fin_path = img_dir / f"{key}__final.png"
                final.save(fin_path)
                ref_path = img_dir / f"{hid}__reference.png"
                if not ref_path.exists():
                    prep["reference"].save(ref_path)
                # Chỉ số G2 (lọt hình bình, đường nối) so ô với ảnh tham chiếu 512x512 nên cần ô cùng kích thước: đo trên
                # bản 512x512 riêng. Ô thật (pat_path) vẫn giữ tỉ lệ gốc để lát lên áo.
                qa_path = img_dir / f"{key}__pattern_qa512.png"
                pat.convert("RGB").resize((512, 512), Image.LANCZOS).save(qa_path)
                qa = assess_design(reference=ref_path, pattern=qa_path, raw=raw_path, final=fin_path,
                                   layout=r["cfg.layout"], template_path=tpl_path, garment_region=region)
                results.append({**r, "status": "completed", "image": f"images/{fin_path.name}",
                                "sha256": sha256_file(fin_path), "tile_size": f"{pat.width}x{pat.height}",
                                "sift_inlier_ratio": round(sift_inlier_ratio(pat, Image.open(PANELS_DIR / f"{hid}.png")), 4),
                                "element_id": extra.get("element_id", ""),
                                **{k: v["value"] for k, v in qa["G2_pattern"]["metrics"].items()},
                                **{k: v["value"] for k, v in qa["G3_final"]["metrics"].items()}})
                print(f"[{len(results)}] {key}", flush=True)
                E.write_results(results, out_dir)         # ghi dần để một lượt sập không làm mất các lượt trước
            except Exception as exc:                       # noqa: BLE001 - lượt lỗi ghi lại, không làm sập cả kế hoạch
                import traceback                           # noqa: PLC0415
                traceback.print_exc()
                results.append({**r, "status": "failed", "error": f"{type(exc).__name__}: {exc}"})
                E.write_results(results, out_dir)
    finally:
        if gen is not None:
            gen.close()
        garment.free_polish_pipe()
    return results


def main(argv: list[str] | None = None) -> int:
    import argparse                                              # noqa: PLC0415
    from tsds.evaluation import experiment as E                       # noqa: PLC0415
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["plan", "run", "analyze"])
    ap.add_argument("--levels", help="chỉ chạy các mức này (cách nhau bằng dấu phẩy), giữ kết quả cũ của các mức còn lại")
    args = ap.parse_args(argv)
    spec = E.load_spec(SPEC)
    out_dir = E.OUT / spec["id"]
    if args.cmd == "analyze":
        E.analyze(out_dir)
        return 0
    rows = E.expand_plan(spec)
    E.write_plan(spec, rows, out_dir)
    print(f"{spec['id']}: {len(rows)} lượt chạy")
    if args.cmd == "run":
        keep: list[dict] = []
        if args.levels:
            import csv                                           # noqa: PLC0415
            only = set(args.levels.split(","))
            old = out_dir / "results.csv"
            if old.exists():
                keep = [r for r in csv.DictReader(old.open(encoding="utf-8")) if r["iv_level"] not in only]
            rows = [r for r in rows if r["iv_level"] in only]
            print(f"Chạy {len(rows)} lượt, giữ {len(keep)} kết quả cũ")
        E.write_results(run(spec, rows, out_dir, keep), out_dir)
        E.analyze(out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
