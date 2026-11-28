"""Kiểm thử đo thời gian: hàm timed/rounded, khối timing trong Passport, và verify() phát hiện sửa số."""
import json
import types

import pytest

from tsds.core import timing
from tsds.provenance import passport as P
from tests.test_passport_garment import tao_passport, thong_tin_ao_lora, work    # noqa: F401  (work là fixture)


def dat_dong_ho(monkeypatch, values):
    """Thay đồng hồ của riêng module timing (không đụng time toàn cục): mỗi lần gọi trả giá trị kế tiếp."""
    it = iter(values)
    monkeypatch.setattr(timing, "time", types.SimpleNamespace(perf_counter=lambda: next(it)))


def tai_lai(pp):
    """Mô phỏng ghi ra JSON rồi đọc lại, để khối generation và sổ cái không còn dùng chung một đối tượng."""
    return json.loads(json.dumps(pp))


def test_timed_cong_don_khi_chay_nhieu_lan(monkeypatch):
    dat_dong_ho(monkeypatch, [0.0, 2.0, 10.0, 13.5])
    store = {}
    with timing.timed(store, "pattern_total_s"):
        pass
    with timing.timed(store, "pattern_total_s"):
        pass
    assert store == {"pattern_total_s": 5.5}          # 2.0 + 3.5


def test_timed_van_ghi_khi_ngoai_le(monkeypatch):
    dat_dong_ho(monkeypatch, [1.0, 4.0])
    store = {}
    with pytest.raises(ValueError):
        with timing.timed(store, "polish_s"):
            raise ValueError("lỗi giả")
    assert store == {"polish_s": 3.0}


def test_rounded_khong_sua_ban_goc():
    goc = {"a": 1.23456, "b": 10.0}
    assert timing.rounded(goc) == {"a": 1.23, "b": 10.0}
    assert goc["a"] == 1.23456


def test_passport_co_khoi_timing_va_nhan_pham_vi(work):    # noqa: F811
    rec_timing = {"pattern_selected_s": 6.1, "pattern_total_s": 12.4, "layout_s": 0.8, "polish_s": 4.2,
                  "quality_s": 1.1, "design_s": 18.9}
    pp = tao_passport(work, thong_tin_ao_lora(work), timing=rec_timing)
    t = pp["generation"]["timing"]
    assert t["design"] == rec_timing and t["schema"] == timing.SCHEMA and t["unit"] == "s"
    assert "KHÔNG cộng" in t["run"]["scope"]
    assert any(e["event"] == "timing" for e in pp["ledger"])
    assert pp["generation"]["duration_s"] == 0.0     # duration_s cũ giữ nguyên nghĩa, không bị ghi đè
    assert P.verify(pp, check_files=False)["ok"]


def test_passport_giu_input_gate_s_trong_khoi_run(work):    # noqa: F811
    run = {"input_gate_s": 3.21, "prepare_s": 0.7, "set_s": 100.0}
    pp = tao_passport(work, thong_tin_ao_lora(work), builder_extra={"run_timing": run},
                      timing={"design_s": 18.9})
    gh = pp["generation"]["timing"]["run"]
    assert gh["input_gate_s"] == 3.21 and gh["set_s"] == 100.0       # ghi riêng, không cộng vào set_s
    assert P.verify(tai_lai(pp), check_files=False)["ok"]
    sua = tai_lai(pp)
    sua["generation"]["timing"]["run"]["input_gate_s"] = 0.1          # sửa số cổng ảnh phải bị phát hiện
    assert not P.verify(sua, check_files=False)["ok"]


def test_passport_cu_khong_co_timing_van_hop_le(work):    # noqa: F811
    pp = tao_passport(work, thong_tin_ao_lora(work))
    assert "timing" not in pp["generation"]
    assert not any(e["event"] == "timing" for e in pp["ledger"])
    assert P.verify(pp, check_files=False)["ok"]


def test_verify_phat_hien_sua_so_thoi_gian(work):          # noqa: F811
    pp = tao_passport(work, thong_tin_ao_lora(work), timing={"design_s": 18.9})
    assert P.verify(tai_lai(pp), check_files=False)["ok"]         # bản đọc lại từ JSON vẫn hợp lệ
    sua = tai_lai(pp)
    sua["generation"]["timing"]["design"]["design_s"] = 5.0       # sửa số ở khối generation, sổ cái giữ số cũ
    kq = P.verify(sua, check_files=False)
    assert not kq["ok"] and any("khối thời gian" in p for p in kq["problems"])
    xoa = tai_lai(pp)
    del xoa["generation"]["timing"]                               # xóa hẳn khối, sổ cái vẫn còn sự kiện timing
    assert any("khối thời gian" in p for p in P.verify(xoa, check_files=False)["problems"])
    sua2 = tai_lai(pp)
    ev = next(e for e in sua2["ledger"] if e["event"] == "timing")
    ev["payload"]["timing"]["design"]["design_s"] = 5.0           # sửa cả sổ cái: chuỗi băm báo sai
    sua2["generation"]["timing"] = ev["payload"]["timing"]
    assert not P.verify(sua2, check_files=False)["ok"]
