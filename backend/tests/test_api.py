# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

# Đảm bảo import app từ cả repo root lẫn thư mục backend/
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest
# pyrefly: ignore [missing-import]
from fastapi.testclient import TestClient

from app.main import app


# ============================================================
# MOCK SUPABASE CLIENT (Không phụ thuộc live DB / secret)
# ============================================================

class MockQueryBuilder:
    def __init__(self, data=None):
        self._data = data

    def select(self, *args, **kwargs):
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def eq(self, column: str, value: str):
        if isinstance(self._data, list):
            filtered = [item for item in self._data if item.get(column) == value]
            return MockQueryBuilder(filtered)
        return self

    def execute(self):
        class MockResponse:
            def __init__(self, data):
                self.data = data
        return MockResponse(self._data)


class MockRPC:
    def __init__(self, fn_name: str, params: dict):
        self.fn_name = fn_name
        self.params = params

    def execute(self):
        class MockResponse:
            def __init__(self, data):
                self.data = data

        p_id = self.params.get("p_heritage_id")
        if p_id == "BT001":
            return MockResponse({
                "heritage_id": "BT001",
                "preserve": ["core_motif", "symbolic_element"],
                "modifiable": [
                    "background",
                    "color_palette",
                    "composition_layout",
                    "material_texture",
                    "product_context",
                ],
                "restricted": [],
                "rule_sources": {
                    "core_motif": "SRC001",
                    "symbolic_element": "SRC001",
                },
                "source_notes": {
                    "core_motif": "SRC001 — Nguyễn Đình Chiến (2019)...",
                    "symbolic_element": "SRC001 — Nguyễn Đình Chiến (2019)...",
                },
                "locators": {
                    "core_motif": "thành lư tạo hình bông sen nở với 3 lớp cánh nổi",
                    "symbolic_element": "thành lư tạo hình bông sen nở với 3 lớp cánh nổi",
                },
            })
        # Trường hợp không tồn tại -> get_rule_base SQL trả null
        return MockResponse(None)


class MockSupabaseClient:
    def table(self, table_name: str):
        if table_name == "sources":
            return MockQueryBuilder([{"source_id": "SRC001"}])
        elif table_name == "heritage_items":
            return MockQueryBuilder([
                {
                    "heritage_id": "BT001",
                    "name": "Hoa sen trên gốm thờ Bát Tràng",
                    "origin": "Bát Tràng",
                    "region": "Hà Nội",
                    "cultural_meaning": "Hoa sen biểu trưng Phật giáo...",
                    "image_path": "heritage/BT001.jpg",
                    "license": "CC-BY",
                },
                {
                    "heritage_id": "BT002",
                    "name": "Rồng trên đồ thờ Bát Tràng",
                    "origin": "Bát Tràng",
                    "region": "Hà Nội",
                    "cultural_meaning": "Rồng cung tiến chùa...",
                    "image_path": "heritage/BT002.jpg",
                    "license": "CC-BY",
                },
            ])
        return MockQueryBuilder([])

    def rpc(self, fn_name: str, params: dict | None = None):
        return MockRPC(fn_name, params or {})


@pytest.fixture
def client(monkeypatch):
    """Fixture cung cấp FastAPI TestClient với Supabase Client đã được mock."""
    mock_instance = MockSupabaseClient()
    monkeypatch.setattr("app.services.heritage_service.get_supabase_client", lambda: mock_instance)
    monkeypatch.setattr("app.supabase_client.get_supabase_client", lambda: mock_instance)
    return TestClient(app)


# ============================================================
# TEST CASES
# ============================================================

def test_root_endpoint(client):
    """1. GET / trả 200 và thông báo chào mừng."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Tai Sinh Di San So AI API đang chạy"}


def test_health_check_ok(client):
    """2. GET /health trả 200 khi Supabase kết nối bình thường."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "supabase": "reachable"}


def test_get_heritage_list(client):
    """3. GET /heritage và /heritage-items trả 200 và danh sách các hiện vật."""
    for path in ("/heritage", "/heritage-items"):
        response = client.get(path)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["heritage_id"] == "BT001"
        assert data[1]["heritage_id"] == "BT002"


def test_get_heritage_item_valid(client):
    """4. GET /heritage/BT001 trả 200 và thông tin hiện vật."""
    response = client.get("/heritage/BT001")
    assert response.status_code == 200
    data = response.json()
    assert data["heritage_id"] == "BT001"
    assert data["name"] == "Hoa sen trên gốm thờ Bát Tràng"
    assert data["origin"] == "Bát Tràng"


def test_get_heritage_item_not_found(client):
    """5. GET /heritage/DOES_NOT_EXIST trả 404."""
    response = client.get("/heritage/DOES_NOT_EXIST")
    assert response.status_code == 404
    assert "không tồn tại" in response.json().get("detail", "")


def test_get_rule_base_valid(client):
    """6. GET /heritage/BT001/rule-base và /rule-base/BT001 trả 200 và đủ 6 nhóm thuộc tính."""
    for path in ("/heritage/BT001/rule-base", "/rule-base/BT001"):
        response = client.get(path)
        assert response.status_code == 200
        data = response.json()
        assert data["heritage_id"] == "BT001"

        # Kiểm tra đủ 6 nhóm trường bắt buộc theo MVP Spec
        for field in ("preserve", "modifiable", "restricted", "rule_sources", "source_notes", "locators"):
            assert field in data, f"Thiếu trường {field} trong Rule Base response"

        assert "core_motif" in data["preserve"]
        assert "symbolic_element" in data["preserve"]
        assert data["rule_sources"]["core_motif"] == "SRC001"
        assert "thành lư" in data["locators"]["core_motif"]
        assert "SRC001" in data["source_notes"]["core_motif"]


def test_get_rule_base_null_fail_closed(client):
    """7. RPC trả null (mã không tồn tại) -> HTTP 404 (Fail-closed)."""
    for path in ("/heritage/BT999_UNKNOWN/rule-base", "/rule-base/BT999_UNKNOWN"):
        response = client.get(path)
        assert response.status_code == 404
        assert "không tồn tại" in response.json().get("detail", "")


def test_unconfigured_or_db_error_returns_503(monkeypatch):
    """8. Thiếu credential / DB lỗi -> HTTP 503."""
    def mock_fail_client():
        raise RuntimeError("SUPABASE_URL chưa được cấu hình trong .env")

    monkeypatch.setattr("app.services.heritage_service.get_supabase_client", mock_fail_client)
    monkeypatch.setattr("app.supabase_client.get_supabase_client", mock_fail_client)
    test_client = TestClient(app)

    # Kiểm tra /health trả 503
    res_health = test_client.get("/health")
    assert res_health.status_code == 503
    assert res_health.json()["status"] == "degraded"

    # Kiểm tra /heritage trả 503
    res_heritage = test_client.get("/heritage")
    assert res_heritage.status_code == 503
    assert "Cấu hình cơ sở dữ liệu chưa sẵn sàng" in res_heritage.json()["detail"]

    # Kiểm tra /heritage/BT001/rule-base trả 503
    res_rule = test_client.get("/heritage/BT001/rule-base")
    assert res_rule.status_code == 503
    assert "Cấu hình cơ sở dữ liệu chưa sẵn sàng" in res_rule.json()["detail"]
