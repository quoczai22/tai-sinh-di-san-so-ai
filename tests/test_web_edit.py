# -*- coding: utf-8 -*-
"""Kiểm thử luồng tải bản chỉnh sửa trên web: quy tắc biểu mẫu, hàm gateway web_ui/api/edit.js, danh sách thiết kế đã tạo.

Chạy bằng Node (không cần trình duyệt, mạng hay Modal): gateway được thử với fetch giả. Đáp án lấy từ đặc tả:
  - EditRequest của API: ID tài khoản bắt đầu bằng TSDS, tối đa 24 ký tự [A-Za-z0-9_-] (API rộng hơn: 2 đến 24 ký tự, không bắt buộc tiền tố), vai designer hoặc qc_officer, mô tả 5 đến 500, công cụ 2 đến 80;
  - ảnh PNG thật, tối đa 3 MB, cạnh dài tối đa 4096 px; khóa ghi lấy từ MODAL_WRITE_KEY (thiếu thì MODAL_KEY);
  - gateway không lộ ngược các trường của API ngoài mã sửa, quyết định G3, trạng thái duyệt; không ghi biểu mẫu vào nhật ký.
"""
from __future__ import annotations

import base64
import io
import json
import os
import shutil
import struct
import subprocess
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
JS = ROOT / "web_ui" / "assets" / "js"
EDIT_JS = ROOT / "web_ui" / "api" / "edit.js"
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="cần Node.js")

PASSPORT = "DP-HV07-20261121T160957-V2"
GOOD = {"editor_id": "TSDS01", "editor_role": "designer", "description": "Tăng độ sáng vùng ngực áo", "tool": "GIMP"}


def _png(size=(8, 8)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, (200, 30, 30)).save(buf, "PNG")
    return buf.getvalue()


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode()


def _png_header_only(width: int, height: int) -> bytes:
    """Tệp có chữ ký PNG và khối IHDR khai báo khổ ảnh; đủ để gateway đọc kích thước, không cần ảnh thật."""
    return b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", width, height) + b"\x08\x02\x00\x00\x00" + b"\0\0\0\0"


def _node_module(script: str) -> dict:
    r = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


# ---------------------------------------------------------------- quy tắc biểu mẫu --

def test_form_rules():
    out = _node_module(f"""
import {{ validateField, validateFile, validateAll, EDIT_LIMITS }} from '{(JS / 'core' / 'edit-rules.js').as_uri()}';
const r = {{
  idOk: validateField('editor_id', 'TSDS01'), idShort: validateField('editor_id', 'a'), idLong: validateField('editor_id', 'TSDS' + 'a'.repeat(21)),
  idAccent: validateField('editor_id', 'TSDSTiến'), idSpace: validateField('editor_id', 'TSDS cd'), idTrim: validateField('editor_id', '  TSDS01  '),
  idMax24: validateField('editor_id', 'TSDS' + 'a'.repeat(20)), idSymbols: validateField('editor_id', 'TSDS_a-1'),
  idNoPrefix: validateField('editor_id', 'NTK01'), idLowerPrefix: validateField('editor_id', 'tsds01'), idOnlyPrefix: validateField('editor_id', 'TSDS'),
  idEmpty: validateField('editor_id', ''),
  roleOk: validateField('editor_role', 'qc_officer'), roleBad: validateField('editor_role', 'admin'),
  descShort: validateField('description', 'abcd'), descOk: validateField('description', 'abcde'), descLong: validateField('description', 'x'.repeat(501)),
  emoji5: validateField('description', '🎨'.repeat(5)), emoji4: validateField('description', '🎨'.repeat(4)),
  emoji500: validateField('description', '🎨'.repeat(500)), emoji501: validateField('description', '🎨'.repeat(501)),
  noTypePng: validateFile({{ type: '', name: 'a.PNG', size: 10 }}), noTypeJpg: validateFile({{ type: '', name: 'a.jpg', size: 10 }}),
  toolShort: validateField('tool', 'G'), toolOk: validateField('tool', 'GIMP'),
  fileNone: validateFile(null), fileJpeg: validateFile({{ type: 'image/jpeg', size: 10 }}), fileEmpty: validateFile({{ type: 'image/png', size: 0 }}),
  fileBig: validateFile({{ type: 'image/png', size: EDIT_LIMITS.maxBytes + 1 }}), fileOk: validateFile({{ type: 'image/png', size: EDIT_LIMITS.maxBytes }}),
  allOk: Object.keys(validateAll({json.dumps(GOOD)})).length, allBad: Object.keys(validateAll({{ editor_id: '', editor_role: '', description: '', tool: '' }})),
}};
console.log(JSON.stringify(r));
""")
    for key in ("idOk", "idTrim", "idMax24", "idSymbols", "roleOk", "descOk", "toolOk", "fileOk", "emoji5", "emoji500", "noTypePng"):
        assert out[key] == "", key
    for key in ("idShort", "idLong", "idAccent", "idSpace", "idNoPrefix", "idLowerPrefix", "idOnlyPrefix", "idEmpty", "roleBad", "descShort", "descLong", "toolShort",
                "fileNone", "fileJpeg", "fileEmpty", "fileBig", "emoji4", "emoji501", "noTypeJpg"):
        assert out[key], key
    assert out["allOk"] == 0
    assert sorted(out["allBad"]) == ["description", "editor_id", "editor_role", "tool"]


# --------------------------------------------------------- gateway: hàm edit.js --

def _gateway(requests: list[dict], upstream: dict | None = None, env: dict | None = None) -> dict:
    driver = r"""
const handler = require(process.env.EDIT_JS);
const input = JSON.parse(process.env.SCENARIO);
const logs = [], calls = [], origLog = console.log;
console.log = (...a) => logs.push(a.join(' '));
global.fetch = async (url, opts) => {
  calls.push({ url, headers: opts.headers, body: JSON.parse(opts.body) });
  return { status: input.upstream.status, ok: input.upstream.status >= 200 && input.upstream.status < 300, json: async () => input.upstream.json };
};
(async () => {
  const out = [];
  for (const s of input.requests) {
    const res = { code: 200, headers: {}, body: null, setHeader(k, v) { this.headers[k] = v; }, status(c) { this.code = c; return this; }, json(b) { this.body = b; return this; } };
    await handler({ method: s.method || 'POST', query: s.query, body: s.body, headers: s.headers || { 'x-forwarded-for': '9.9.9.9' } }, res);
    out.push({ code: res.code, body: res.body });
  }
  console.log = origLog;
  process.stdout.write(JSON.stringify({ out, calls, logs }));
})();
"""
    scenario = {"requests": requests, "upstream": upstream or {"status": 200, "json": {"edit_id": "E1", "approval_status": "pending_expert_review", "quality_decision": "PASS"}}}
    base_env = {**os.environ, "EDIT_JS": str(EDIT_JS), "SCENARIO": json.dumps(scenario), "MODAL_URL": "https://modal.test", "MODAL_KEY": "k_main",
                "MODAL_WRITE_KEY": "k_write", "EDIT_RATE_LIMIT_PER_HOUR": "50", **(env or {})}
    r = subprocess.run(["node", "-e", driver], capture_output=True, text=True, encoding="utf-8", env=base_env)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def _req(body: dict | None = None, **over) -> dict:
    body = {**GOOD, "image_png_base64": _b64(_png()), **(body or {})}
    return {"query": {"id": PASSPORT}, "body": body, **over}


def test_gateway_forwards_valid_edit_with_write_key_and_hides_extra_fields():
    r = _gateway([_req()], upstream={"status": 200, "json": {"edit_id": "E1", "approval_status": "pending_expert_review", "quality_decision": "PASS",
                                                          "editor_id": "TSDS01", "after_path": "outputs/edits/x/v2_human_edit.png"}})
    assert r["out"][0] == {"code": 200, "body": {"edit_id": "E1", "approval_status": "pending_expert_review", "quality_decision": "PASS"}}
    (call,) = r["calls"]
    assert call["url"] == f"https://modal.test/passports/{PASSPORT}/edits"
    assert call["headers"]["X-API-Key"] == "k_write"
    assert call["body"]["editor_id"] == "TSDS01" and call["body"]["editor_role"] == "designer" and call["body"]["tool"] == "GIMP"


def test_gateway_falls_back_to_modal_key_when_no_write_key():
    r = _gateway([_req()], env={"MODAL_WRITE_KEY": ""})
    assert r["calls"][0]["headers"]["X-API-Key"] == "k_main"


def test_gateway_trims_text_fields_before_forwarding():
    r = _gateway([_req({"editor_id": "  TSDS01 ", "description": "  Tăng độ sáng vùng ngực  ", "tool": " GIMP "})])
    sent = r["calls"][0]["body"]
    assert sent["editor_id"] == "TSDS01" and sent["description"] == "Tăng độ sáng vùng ngực" and sent["tool"] == "GIMP"


@pytest.mark.parametrize("override, code", [
    ({"editor_id": "a"}, 400), ({"editor_id": "Tiến Đoàn"}, 400), ({"editor_role": "admin"}, 400),
    ({"description": "abcd"}, 400), ({"tool": "G"}, 400), ({"image_png_base64": 123}, 400),
    ({"image_png_base64": "***not-base64***"}, 400), ({"image_png_base64": ""}, 400),
])
def test_gateway_rejects_invalid_fields(override, code):
    r = _gateway([_req(override)])
    assert r["out"][0]["code"] == code and r["calls"] == []


def test_gateway_requires_tsds_prefix_for_account_id():
    ids = ["TSDS01", "TSDS" + "a" * 20, "TSDS_a-1", "TSDS" + "a" * 21, "TSDS", "tsds01", "NTK01", "XTSDS01", "TSDS 01"]
    r = _gateway([_req({"editor_id": i}) for i in ids])
    assert [x["code"] for x in r["out"]] == [200, 200, 200, 400, 400, 400, 400, 400, 400]


def test_gateway_counts_characters_like_the_api():
    """API (Pydantic) đếm điểm mã: 5 biểu tượng là 5 ký tự (đạt), 4 là 4 (không đạt), 500 đạt, 501 không đạt."""
    r = _gateway([_req({"description": "🎨" * 5}), _req({"description": "🎨" * 4}), _req({"description": "🎨" * 500}),
                  _req({"description": "🎨" * 501}), _req({"tool": "🎨" * 80}), _req({"tool": "🎨" * 81})])
    assert [x["code"] for x in r["out"]] == [200, 400, 200, 400, 200, 400]


def test_gateway_rejects_non_png_oversized_and_huge_dimensions():
    jpeg = io.BytesIO()
    Image.new("RGB", (8, 8)).save(jpeg, "JPEG")
    r = _gateway([_req({"image_png_base64": _b64(jpeg.getvalue())}),
                  _req({"image_png_base64": _b64(_png_header_only(5000, 100))}),
                  _req({"image_png_base64": _b64(_png_header_only(100, 4097))}),
                  _req({"image_png_base64": _b64(_png_header_only(4096, 4096))}),
                  _req({"image_png_base64": _b64(_png_header_only(8, 8) + b"\0" * (3 * 1024 * 1024))})])
    assert [x["code"] for x in r["out"]] == [400, 400, 400, 200, 413]
    assert len(r["calls"]) == 1                                  # chỉ ảnh 4096 x 4096 hợp lệ được chuyển tiếp


def test_gateway_accepts_data_url_prefix():
    r = _gateway([_req({"image_png_base64": "data:image/png;base64," + _b64(_png())})])
    assert r["out"][0]["code"] == 200 and not r["calls"][0]["body"]["image_png_base64"].startswith("data:")


def test_gateway_rejects_bad_method_and_passport_id():
    r = _gateway([{"method": "GET", "query": {"id": PASSPORT}, "body": {}}, _req() | {"query": {"id": "../etc/passwd"}},
                  _req() | {"query": {"id": "DP-HV07-20261121T160957-V2/../x"}}])
    assert [x["code"] for x in r["out"]] == [405, 400, 400] and r["calls"] == []


def test_gateway_maps_upstream_errors_without_leaking_details():
    for status, expected in ((404, 404), (401, 503), (403, 503), (422, 422), (413, 413), (500, 502)):
        r = _gateway([_req()], upstream={"status": status, "json": {"detail": "chi tiết nội bộ SECRET"}})
        assert r["out"][0]["code"] == expected, status
        assert "SECRET" not in json.dumps(r["out"][0]["body"]), status


def test_gateway_rate_limits_per_ip():
    r = _gateway([_req(), _req(), _req(), _req() | {"headers": {"x-forwarded-for": "8.8.8.8"}}], env={"EDIT_RATE_LIMIT_PER_HOUR": "2"})
    assert [x["code"] for x in r["out"]] == [200, 200, 429, 200]


def test_gateway_unconfigured_returns_503():
    r = _gateway([_req()], env={"MODAL_URL": "", "MODAL_KEY": ""})
    assert r["out"][0]["code"] == 503 and r["calls"] == []


def test_gateway_does_not_log_form_content():
    r = _gateway([_req({"editor_id": "TSDSKIEM01", "description": "mô tả riêng tư kiểm tra", "tool": "CongCuRieng"})])
    text = " ".join(r["logs"])
    assert "gateway_edit" in text and PASSPORT in text
    for secret in ("TSDSKIEM01", "mô tả riêng tư kiểm tra", "CongCuRieng", _b64(_png())[:20], "k_write"):
        assert secret not in text


def test_vercel_routes_edit_before_generic_live_route():
    cfg = json.loads((ROOT / "web_ui" / "vercel.json").read_text(encoding="utf-8"))
    sources = [r["source"] for r in cfg["rewrites"]]
    assert sources.index("/api/live/passports/:id/edits") < sources.index("/api/live/:route*")
    assert cfg["functions"]["api/edit.js"]["maxDuration"] <= 60


# ------------------------------------------------ danh sách thiết kế đã tạo (data.js) --

def test_my_runs_remember_dedupe_cap_and_forget():
    out = _node_module(f"""
const store = new Map();
globalThis.window = {{}};
globalThis.localStorage = {{ getItem: (k) => (store.has(k) ? store.get(k) : null), setItem: (k, v) => store.set(k, String(v)) }};
const data = await import('{(JS / 'core' / 'data.js').as_uri()}');
const r = {{ empty: data.myRuns().length }};
data.activateLive('LR3D_33', 'R20261121T160957-HV07', []);
data.activateLive('LR3D_61', 'R20261121T161446-HV10', []);
data.activateLive('LR3D_33', 'R20261121T160957-HV07', []);              // tạo lại cùng lượt: không trùng, lên đầu danh sách
r.order = data.myRuns().map((x) => x.runId);
data.forgetRun('R20261121T161446-HV10');
r.afterForget = data.myRuns().map((x) => x.runId);
for (let i = 0; i < 20; i++) data.activateLive('LR3D_33', 'R2026112' + String(i).padStart(2, '0') + 'T000000-HV07', []);
r.capped = data.myRuns().length;
r.newest = data.myRuns()[0].runId;
store.set('dh:my-runs', '{{hỏng');                                       // dữ liệu hỏng không làm sập trang
r.corrupt = data.myRuns().length;
store.set('dh:my-runs', JSON.stringify([{{ heritageId: 'a' }}, {{ runId: 'b' }}, null]));   // bản ghi thiếu trường bị bỏ
r.incomplete = data.myRuns().length;
console.log(JSON.stringify(r));
""")
    assert out["empty"] == 0
    assert out["order"] == ["R20261121T160957-HV07", "R20261121T161446-HV10"]      # lượt tạo lại lên đầu, không trùng
    assert out["afterForget"] == ["R20261121T160957-HV07"]
    assert out["capped"] == 12 and out["newest"] == "R202611219T000000-HV07" and out["corrupt"] == 0 and out["incomplete"] == 0


def test_init_survives_malformed_hash_and_edit_clears_stale_snapshot():
    out = _node_module(f"""
const store = new Map();
globalThis.window = {{}};
globalThis.location = {{ hash: '#/result/%E0%A4%A' }};                   // tham số sai định dạng: decodeURIComponent sẽ ném lỗi
globalThis.localStorage = {{ getItem: (k) => (store.has(k) ? store.get(k) : null), setItem: (k, v) => store.set(k, String(v)) }};
globalThis.fetch = async () => ({{ ok: true, status: 200, json: async () => ({{ edit_id: 'E1' }}) }});
const data = await import('{(JS / 'core' / 'data.js').as_uri()}');
const r = {{}};
try {{ const info = await data.init(); r.initMode = info.mode; }} catch (e) {{ r.initError = String(e); }}
data.activateLive('LR3D_33', 'R20261121T160957-HV07', [{{ status: 'completed', image_url: '/x.png', passport_id: 'DP-A', run_id: 'R20261121T160957-HV07' }}]);
r.beforeEdit = data.liveDesignsFor('LR3D_33')?.length ?? null;
await data.submitEdit('DP-HV07-20261121T160957-V2', {{}});
r.afterEdit = data.liveDesignsFor('LR3D_33');
console.log(JSON.stringify(r));
""")
    assert out.get("initError") is None and out["initMode"] == "demo"
    assert out["beforeEdit"] == 1 and out["afterEdit"] is None


def test_refresh_health_recovers_when_first_health_call_failed():
    """Lần gọi /health đầu quá chậm (torch còn nạp) làm init() coi như không có GPU; refreshHealth() hỏi lại và sửa được."""
    out = _node_module(f"""
globalThis.window = {{ DH_API_BASE: 'http://127.0.0.1:8000' }};
globalThis.location = {{ hash: '#/studio/LR3D_33' }};
globalThis.localStorage = {{ getItem: () => null, setItem: () => {{}} }};
let healthCalls = 0;
globalThis.fetch = async (url) => {{
    if (String(url).endsWith('/health')) {{
        healthCalls += 1;
        if (healthCalls === 1) throw new DOMException('timeout', 'AbortError');         // lần đầu: quá hạn chờ
        return {{ ok: true, status: 200, json: async () => ({{ generation_available: true }}) }};
    }}
    return {{ ok: true, status: 200, json: async () => ({{}}) }};
}};
const data = await import('{(JS / 'core' / 'data.js').as_uri()}');
await data.init();
const r = {{ afterInit: data.canGenerate() }};
r.refreshed = await data.refreshHealth();
r.afterRefresh = data.canGenerate();
console.log(JSON.stringify(r));
""")
    assert out == {"afterInit": False, "refreshed": True, "afterRefresh": True}


def test_generation_drops_a_stale_pending_job_and_starts_a_new_one():
    """Trình duyệt còn nhớ lượt tạo đã bị xóa khỏi máy chủ (404): phải bỏ nó và tạo lượt mới, không kẹt ở lượt cũ."""
    out = _node_module(f"""
const store = new Map([['dh:pending-generation', JSON.stringify({{ heritageId: 'LR3D_33', jobId: 'a'.repeat(32), startedAt: Date.now() }})]]);
globalThis.window = {{ DH_API_BASE: 'http://x' }};
globalThis.location = {{ hash: '#/studio/LR3D_33' }};
globalThis.localStorage = {{ getItem: (k) => (store.has(k) ? store.get(k) : null), setItem: (k, v) => store.set(k, String(v)), removeItem: (k) => store.delete(k) }};
const calls = [];
const reply = (status, body) => ({{ ok: status < 400, status, json: async () => body }});
globalThis.fetch = async (url, opts = {{}}) => {{
    calls.push((opts.method || 'GET') + ' ' + String(url).replace('http://x', ''));
    if (String(url).includes('/generate/' + 'a'.repeat(32))) return reply(404, {{ detail: 'Không tìm thấy job.' }});
    if (String(url).endsWith('/generate')) return reply(200, {{ job_id: 'b'.repeat(32) }});
    if (String(url).includes('/generate/' + 'b'.repeat(32))) return reply(200, {{ status: 'completed', run_id: 'R1', variants: [], progress: 100 }});
    return reply(200, {{}});
}};
const {{ runGeneration }} = await import('{(JS / 'core' / 'generation.js').as_uri()}');
const job = await runGeneration('LR3D_33', null);
console.log(JSON.stringify({{ runId: job.run_id, posted: calls.some((c) => c.startsWith('POST') && c.endsWith('/generate')), pending: store.get('dh:pending-generation') ?? null }}));
""")
    assert out == {"runId": "R1", "posted": True, "pending": None}
