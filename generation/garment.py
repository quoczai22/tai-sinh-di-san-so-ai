# -*- coding: utf-8 -*-
"""GIAI ĐOẠN 2 — đưa hoa văn lên áo dài (v6).

Ghép ảnh TẤT ĐỊNH, không dùng model sinh ảnh. Ba lý do:

1. Dáng áo dài luôn đúng — không phụ thuộc việc SD1.5 có "biết" áo dài hay
   không. Rủi ro mà v6 mục 12 xếp mức Cao được gỡ bằng kiến trúc, không phải
   bằng prompt engineering.
2. Tái lập 100%: cùng hoa văn + cùng ảnh mẫu → cùng kết quả, không cần seed.
3. Áo giữ nguyên giữa mọi thiết kế, nên khi so sánh 4 mức Creative Intensity thì
   khác biệt đến từ HOA VĂN chứ không phải từ việc SD vẽ cái áo khác đi.
"""
from __future__ import annotations

import json
import sys
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

for _s in (sys.stdout, sys.stderr):
    if getattr(_s, "encoding", "").lower().replace("-", "") != "utf8":
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

ROOT = Path(__file__).resolve().parent.parent
GARMENT_DIR = ROOT / "data" / "garment"
TEMPLATE = GARMENT_DIR / "aodai_template.png"
LAYOUTS_FILE = GARMENT_DIR / "layouts.json"

FALLBACK_LAYOUT = {"label": "Dải thân trước", "regions": [[0.30, 0.02, 0.70, 0.72]],
                   "scale": 1.6}


def load_layouts() -> dict:
    if LAYOUTS_FILE.exists():
        return json.loads(LAYOUTS_FILE.read_text(encoding="utf-8"))
    return {"layouts": {"front_panel": FALLBACK_LAYOUT}, "default": "front_panel"}


def layout_names() -> list[str]:
    return list(load_layouts()["layouts"])


def get_layout(name: str | None = None) -> dict:
    cfg = load_layouts()
    key = name or cfg.get("default", "front_panel")
    if key not in cfg["layouts"]:
        raise KeyError(f"Khong co layout {key!r}. Co: {list(cfg['layouts'])}")
    return {**cfg["layouts"][key], "name": key}


def garment_mask(template: Image.Image) -> np.ndarray:
    """Tách vùng ÁO trắng khỏi nền, bằng độ bão hoà thấp + độ sáng cao.

    Bản trước dùng "pixel đủ sáng" nên bãi cỏ và bầu trời cũng lọt, hoa văn tràn
    ra ngoài áo. Vải áo dài trắng có đặc trưng riêng: bão hoà rất thấp. Cỏ xanh
    bão hoà cao dù sáng, nên tách được sạch.

    Sau đó giữ MỘT thành phần liên thông lớn nhất — loại các mảng trắng lẻ trong
    nền (mây, vệt nắng).
    """
    hsv = cv2.cvtColor(np.array(template), cv2.COLOR_RGB2HSV)
    s, v = hsv[:, :, 1].astype(np.int16), hsv[:, :, 2].astype(np.int16)
    m = ((s < 45) & (v > 140)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    if n > 1:
        biggest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        m = (lab == biggest).astype(np.uint8)
    return m


def displacement_map(template: Image.Image, strength: float = 14.0,
                     smooth: float = 6.0) -> tuple[np.ndarray, np.ndarray]:
    """Trường dịch chuyển suy từ bóng đổ của vải, để uốn hoa văn theo nếp gấp.

    Vì sao cần: dán hoa văn phẳng lên ảnh thì nó nằm thẳng đơ trong khi vải bên
    dưới có nếp — mắt nhận ra ngay là ghép. Độ sáng của vải trắng chính là bản
    đồ chiều cao gần đúng của bề mặt: chỗ lõm thì tối, chỗ nhô thì sáng. Lấy đạo
    hàm của nó ra được hướng dốc, rồi đẩy hoa văn theo hướng đó.

    Đây là kỹ thuật displacement map tiêu chuẩn trong ghép ảnh, tất định hoàn toàn.
    """
    g = np.array(template.convert("L")).astype(np.float32)
    g = cv2.GaussianBlur(g, (0, 0), smooth)
    dx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=5)
    dy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=5)
    n = max(np.abs(dx).max(), np.abs(dy).max(), 1e-6)
    h, w = g.shape
    Y, X = np.mgrid[0:h, 0:w].astype(np.float32)
    return X + dx / n * strength, Y + dy / n * strength


def shading_map(template: Image.Image, mask: np.ndarray, boost: float = 1.9) -> np.ndarray:
    """Bản đồ truyền sáng của vải, chuẩn hoá quanh 1,0 rồi tăng tương phản.

    Vì sao cần dù đã nhân với ảnh nền: vải áo dài trắng gần bão hoà (~245-255),
    nên `base * pattern / 255` gần bằng chính pattern — nếp gấp gần như biến mất
    và hoa văn phẳng lì. Mắt nhận ra ngay là đề can dán lên ảnh.

    Cách sửa: tách riêng độ sáng của vùng vải, chia cho trung vị của chính nó để
    được hệ số quanh 1,0, rồi khuếch đại độ lệch. Chỗ nếp gấp (<1) làm hoa văn
    tối đi, chỗ hứng sáng (>1) làm nó sáng lên — đúng cách vải thật phản chiếu.

    Đây là bước displacement map KHÔNG làm được: nó chỉ uốn hình học, không xử lý
    truyền sáng.
    """
    lum = np.array(template.convert("L")).astype(np.float32)
    sel = lum[mask > 0.15]
    ref = float(np.median(sel)) if sel.size else float(np.median(lum))
    g = lum / max(ref, 1e-3)
    g = 1.0 + (g - 1.0) * boost                      # khuếch đại nếp gấp
    return np.clip(cv2.GaussianBlur(g, (0, 0), 1.2), 0.45, 1.35)


def grade_to_scene(pattern: Image.Image, template: Image.Image,
                   desaturate: float = 0.20, wb: float = 0.35) -> Image.Image:
    """Hạ bão hoà và kéo cân bằng trắng của hoa văn về tông ảnh nền.

    Hoa văn do SD sinh thường rực (vàng chanh, cyan, magenta) trong khi ảnh nền
    chụp ngoài trời có tông dịu hơi ngả xám. Chênh lệch đó khiến mắt tách được
    ngay hai lớp ảnh khác nguồn.
    """
    a = np.array(pattern.convert("RGB")).astype(np.uint8)
    hsv = cv2.cvtColor(a, cv2.COLOR_RGB2HSV).astype(np.float32)
    hsv[:, :, 1] *= (1.0 - desaturate)
    a = cv2.cvtColor(np.clip(hsv, 0, 255).astype(np.uint8), cv2.COLOR_HSV2RGB)

    # Cân bằng trắng chỉ đụng SẮC, không đụng ĐỘ SÁNG: làm trong LAB và chỉ dịch
    # hai kênh a/b. Dịch cả ba kênh RGB về trung bình ảnh nền sẽ kéo luôn độ sáng
    # về phía nền (cỏ + trời + vải trắng) và hoa văn bạc trắng hết.
    lab = cv2.cvtColor(a, cv2.COLOR_RGB2LAB).astype(np.float32)
    tlab = cv2.cvtColor(np.array(template.convert("RGB")), cv2.COLOR_RGB2LAB).astype(np.float32)
    for c in (1, 2):
        lab[:, :, c] += (tlab[:, :, c].mean() - lab[:, :, c].mean()) * wb
    out = cv2.cvtColor(np.clip(lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2RGB)
    return Image.fromarray(out)


def _feather(mask: np.ndarray, px: float) -> np.ndarray:
    """Làm mềm mép rất mạnh để hoa văn TAN dần vào vải thay vì bị cắt ngang."""
    return cv2.GaussianBlur(mask.astype(np.float32), (0, 0), max(px, 0.1))


def _layout_mask(template: Image.Image, layout: dict) -> np.ndarray:
    """Hợp các vùng của layout, GIAO với vùng áo — hoa văn không tràn ra ngoài áo.

    Toạ độ tính theo tỉ lệ hộp bao của ÁO, không phải của cả ảnh: đổi ảnh mẫu
    (đổi seed, đổi nền, đổi khung hình) thì layout vẫn còn đúng.
    """
    g = garment_mask(template)
    ys, xs = np.where(g > 0)
    if len(xs) == 0:
        raise RuntimeError("Khong tach duoc vung ao trong anh mau — kiem tra lai anh.")
    gx0, gy0 = int(xs.min()), int(ys.min())
    gw, gh = int(xs.max()) - gx0, int(ys.max()) - gy0

    # Mỗi vùng dựng bằng một trường suy giảm MỀM chứ không phải hộp chữ nhật.
    # Hộp chữ nhật cho mép cắt thẳng đứng/ngang — không áo dài nào có mảng in
    # vuông vức, và mắt nhận ra ngay là hình dán chứ không phải vải in.
    band = np.zeros(g.shape, np.float32)
    for r in layout["regions"]:
        x0, y0 = gx0 + r[0] * gw, gy0 + r[1] * gh
        x1, y1 = gx0 + r[2] * gw, gy0 + r[3] * gh
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        rx, ry = max((x1 - x0) / 2, 1), max((y1 - y0) / 2, 1)
        Y, X = np.mgrid[0:g.shape[0], 0:g.shape[1]].astype(np.float32)
        # Chuẩn Lp với p lớn -> hình gần chữ nhật nhưng bo góc, không có cạnh cứng
        p = 4.0
        d = (np.abs((X - cx) / rx) ** p + np.abs((Y - cy) / ry) ** p) ** (1 / p)
        # Đậm ĐỀU trong gần hết vùng, chỉ nhoè ở dải sát mép. Suy giảm từ tâm
        # làm giữa panel đậm mà rìa nhạt — trông như phun sơn, không như in vải.
        core = float(layout.get("core", 0.82))
        f = np.clip((1.0 - d) / max(1.0 - core, 1e-3), 0, 1)
        band = np.maximum(band, 0.5 - 0.5 * np.cos(np.pi * f))

    m = g.astype(np.float32) * band
    return _feather(m, layout.get("feather", 14.0))


def apply(pattern: Image.Image, layout: str | None = None, opacity: float = 0.92,
          template_path: Path = TEMPLATE, grade: bool = True) -> Image.Image:
    """Đắp hoa văn lên áo dài theo một cách bố trí (layout).

    Dùng phép nhân chứ không dán đè: nếp gấp và bóng đổ của vải vẫn hiện qua hoa
    văn, nên trông như in trên vải thật thay vì dán một hình phẳng lên ảnh.
    """
    if not template_path.exists():
        raise FileNotFoundError(
            f"Chưa có ảnh áo dài mẫu: {template_path}\n"
            f"  Chạy `python -m generation.garment --make-template` để sinh.")
    lay = get_layout(layout)
    tpl = Image.open(template_path).convert("RGB")
    W, H = tpl.size
    mask = _layout_mask(tpl, lay)

    # Hoa văn nay LIỀN MẠCH sẵn (sinh với circular padding), nên lát thẳng là đủ.
    # Không còn lát gương — cách đó tạo đối xứng kaleidoscope, xa nét vẽ men gốm.
    if grade:
        pattern = grade_to_scene(pattern, tpl)
    ys, xs = np.where(mask > 0.05)
    mw = int(xs.max() - xs.min()) + 1
    tw = max(16, int(mw * lay.get("scale", 1.0)))
    tile = np.asarray(pattern.resize(
        (tw, max(1, int(tw * pattern.height / pattern.width))), Image.LANCZOS))
    th = tile.shape[0]
    big = np.tile(tile, (int(np.ceil(H / th)) + 2, int(np.ceil(W / tw)) + 2, 1))
    oy = max(0, int(big.shape[0] / 2 - (ys.min() + ys.max()) / 2))
    ox = max(0, int(big.shape[1] / 2 - (xs.min() + xs.max()) / 2))
    canvas = big[oy:oy + H, ox:ox + W]

    # Uốn theo nếp vải — biến dạng HÌNH HỌC
    mx, my = displacement_map(tpl, strength=lay.get("displace", 14.0))
    warped = cv2.remap(canvas, mx, my, cv2.INTER_LINEAR,
                       borderMode=cv2.BORDER_REFLECT).astype(np.float32)

    # Truyền SÁNG — thứ displacement map không làm được. Nhân bản đồ độ sáng của
    # vải lên hoa văn để nó tối ở nếp gấp và sáng ở chỗ hứng nắng.
    warped *= shading_map(tpl, mask)[:, :, None]

    base = np.asarray(tpl, np.float32)
    m = np.clip(mask * opacity, 0, 1)[:, :, None]
    blended = base * (1 - m) + np.clip(warped, 0, 255) * m
    return Image.fromarray(np.clip(blended, 0, 255).astype(np.uint8))


POLISH_PROMPT = ("a woman wearing an elegant Vietnamese ao dai with a printed silk pattern, "
                 "the print follows the fabric folds naturally, professional fashion "
                 "photograph, soft daylight")
POLISH_NEG = ("flat pasted graphic, sticker, wallpaper, collage, cut out, tiled repeat, "
              "harsh edges, deformed hands, extra limbs, blurry, watermark, text")


@lru_cache(maxsize=1)
def _img2img_pipe():
    """Nạp một lần rồi giữ lại — nạp lại mỗi lần gọi tốn ~10s vô ích khi chạy
    cả bộ 24 thiết kế."""
    import os                                                 # noqa: PLC0415
    import torch                                              # noqa: PLC0415
    from diffusers import (StableDiffusionImg2ImgPipeline,    # noqa: PLC0415
                           UniPCMultistepScheduler)
    from .stable_diffusion import load_env                    # noqa: PLC0415
    load_env()
    pipe = StableDiffusionImg2ImgPipeline.from_pretrained(
        os.environ["SD15_MODEL_ID"], dtype=torch.float16, variant="fp16",
        safety_checker=None, requires_safety_checker=False)
    pipe.scheduler = UniPCMultistepScheduler.from_config(pipe.scheduler.config)
    if torch.cuda.get_device_properties(0).total_memory < 8 * 1024**3:
        pipe.enable_model_cpu_offload()
    else:
        pipe.to("cuda")
    pipe.enable_attention_slicing()
    return pipe


def free_polish_pipe() -> None:
    """Giải phóng VRAM sau khi xong (spec mục 18)."""
    import torch                                              # noqa: PLC0415
    _img2img_pipe.cache_clear()
    torch.cuda.empty_cache()


def polish(composite: Image.Image, strength: float = 0.40, seed: int = 42,
           steps: int = 30) -> Image.Image:
    """Lượt hoàn thiện bằng img2img — biến "hoa văn dán lên ảnh" thành "vải in".

    Ghép ảnh tất định làm được đúng chỗ và đúng dáng, nhưng không làm được ba
    thứ: hoà hoa văn vào sợi vải, phá tính lặp máy móc của lát gạch, và tạo biến
    thiên tự nhiên ở nếp gấp. img2job ở denoise thấp làm cả ba.

    `strength` 0,25-0,35 là vùng an toàn: đủ để hoà vào vải, chưa đủ để SD vẽ lại
    hoa văn thành thứ khác. Trên 0,45 thì hoạ tiết gốc bắt đầu biến dạng.

    Bước này ĐƯA LẠI tính bất định vào giai đoạn 2 — nên seed phải ghi vào nhật ký.
    """
    import torch                                              # noqa: PLC0415
    pipe = _img2img_pipe()
    return pipe(prompt=POLISH_PROMPT, negative_prompt=POLISH_NEG,
                image=composite, strength=strength, num_inference_steps=steps,
                guidance_scale=7.0,
                generator=torch.Generator("cuda").manual_seed(seed)).images[0]


def make_template(seed: int = 43) -> Path:
    """Sinh ảnh áo dài trắng trơn MỘT LẦN rồi dùng lại mãi.

    seed 43 chọn theo pilot: trong 3 seed thử, đây là ảnh cho dáng chính diện,
    tà và ống quần rõ nhất.
    """
    import torch                                              # noqa: PLC0415
    from diffusers import StableDiffusionPipeline, UniPCMultistepScheduler  # noqa: PLC0415
    from .prompt_template import GARMENT_NEG, GARMENT_PROMPT  # noqa: PLC0415
    from .stable_diffusion import load_env                    # noqa: PLC0415
    import os                                                 # noqa: PLC0415

    load_env()
    GARMENT_DIR.mkdir(parents=True, exist_ok=True)
    pipe = StableDiffusionPipeline.from_pretrained(
        os.environ["SD15_MODEL_ID"], dtype=torch.float16, variant="fp16",
        safety_checker=None, requires_safety_checker=False)
    pipe.scheduler = UniPCMultistepScheduler.from_config(pipe.scheduler.config)
    pipe.to("cuda"); pipe.enable_attention_slicing()
    img = pipe(prompt=GARMENT_PROMPT, negative_prompt=GARMENT_NEG,
               num_inference_steps=30, guidance_scale=7.5,
               generator=torch.Generator("cuda").manual_seed(seed)).images[0]
    del pipe; torch.cuda.empty_cache()
    img.save(TEMPLATE)
    PANEL_FILE.write_text(json.dumps({"panel": DEFAULT_PANEL,
                                      "note": "x0,y0,x1,y1 theo tỉ lệ 0-1 của ảnh mẫu"},
                                     ensure_ascii=False, indent=2), encoding="utf-8")
    return TEMPLATE


if __name__ == "__main__":
    if "--make-template" in sys.argv:
        print(f"Da sinh {make_template()}")
