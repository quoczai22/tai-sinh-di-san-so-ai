"""Kiểm thử bộ lọc caption của scripts/data_prep/filter_vietfashion.py (không cần dữ liệu hay GPU)."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("loc", Path(__file__).resolve().parents[1] / "scripts" / "data_prep" / "filter_vietfashion.py")
loc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loc)


def test_giu_ao_dai_co_tru_tay_dai():
    ok, _ = loc.caption_ok("A photo of an elegant Vietnamese áo dài in blue silk with a mandarin collar, long sleeves.")
    assert ok


def test_loai_khi_khong_co_co_tru():
    ok, why = loc.caption_ok("A photo of an elegant Vietnamese áo dài with a rounded neckline and long sleeves.")
    assert not ok and "cổ trụ" in why


def test_loai_khong_tay_va_dang_ngan():
    for cap in ("... mandarin collar, sleeveless ...", "... a mandarin collar and a short tunic ...",
                "... mandarin collar, midi length ...", "... mandarin collar, strapless ..."):
        assert not loc.caption_ok(cap)[0], cap


def test_short_sleeves_khong_bi_loai_nham():
    # "short sleeves" là tay áo ngắn, không phải tà áo ngắn
    assert loc.caption_ok("... a mandarin collar with short sleeves and a long panel ...")[0]


def test_khong_phan_biet_hoa_thuong():
    assert loc.caption_ok("A photo of ... Mandarin Collar ...")[0]
    assert not loc.caption_ok("A photo of ... MANDARIN COLLAR, SLEEVELESS ...")[0]


def test_loai_do_dai_den_goi():
    assert not loc.caption_ok("... mandarin collar, knee-length hem ...")[0]
    assert not loc.caption_ok("... mandarin collar and short length ...")[0]
    assert loc.caption_ok("... mandarin collar and ankle-length hem ...")[0]


def test_chon_theo_ba_dieu_kien():
    spec2 = importlib.util.spec_from_file_location("xuat", Path(__file__).resolve().parents[1] / "scripts" / "data_prep" / "export_lora_set.py")
    xuat = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(xuat)
    def r(cap, a, d): return {"caption": cap, "ao_dai_nguoi": str(a), "dai_san": str(d)}
    rows = [r("fitted tunic", 0.9, 0.9),      # giữ
            r("loose silhouette", 0.9, 0.9),  # không ôm thân
            r("Fitted tunic", 0.79, 0.9),     # CLIP áo dài thấp
            r("fitted tunic", 0.9, 0.69),     # tà ngắn
            r("fitted tunic", 0.8, 0.7)]      # đúng ngưỡng, giữ
    assert [x["ao_dai_nguoi"] for x in xuat.chon(rows)] == ["0.9", "0.8"]
