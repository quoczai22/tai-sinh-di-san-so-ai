# Rà soát Backend & Database — 01/09/2026

> Đối tượng: DevOps/Software Engineer
> Phạm vi: `backend/`, `db/schema.sql`, cấu hình `.env`
> Trạng thái kết nối: **Supabase đã hoạt động**, 7/7 bảng đã tạo, RPC `get_rule_base` chạy được

## Cách kiểm chứng

Mọi lỗi dưới đây đều **chạy thật** để xác nhận, không phải đọc code suy đoán:

- Cài `backend/requirements.txt`, import `app.main` và `app.config` từ hai thư mục làm việc khác nhau
- Gọi `TestClient` lên `/` và `/health`
- Kết nối Supabase thật, `select count(*)` trên cả 7 bảng, gọi RPC `get_rule_base('BT001')`
- Đối chiếu từng trường của `data/sources.json`, `data/rule_base.json`, `data/corpus/*.json` với cột trong `db/schema.sql`
- Đối chiếu `audit_log` với danh sách trường ở spec mục 14.2

---

## Tổng quan

| # | Lỗi | Mức | Vị trí |
|---|---|---|---|
| B1 | `SUPABASE_DB_CONNECTION_STRING` luôn rỗng do sai tên biến | 🔴 Chặn | `backend/app/config.py` + `.env` |
| B2 | Chạy từ `backend/` thì toàn bộ config rỗng | 🔴 Chặn | `backend/app/config.py` |
| B3 | `/health` báo `ok` kể cả khi DB hỏng | 🟡 | `backend/app/main.py` |
| B4 | `get_supabase_client()` thất bại im lặng | 🟡 | `backend/app/supabase_client.py` |
| D1 | `rule_entries` không có cột lưu `source_note` — mất 52 câu trích | 🔴 Chặn | `db/schema.sql` |
| D2 | `sources` mất 11/15 trường, đặc biệt `rule_basis` | 🔴 Chặn | `db/schema.sql` |
| D3 | `document_chunks` thiếu `locator`/`page`/`section` | 🟠 | `db/schema.sql` |
| D4 | `audit_log` thiếu `rule_base_snapshot` | 🟠 | `db/schema.sql` |

Điểm tốt cần giữ: `.env` đã gitignore và **chưa từng lọt vào lịch sử git** (đã kiểm tra `git log --all`). Ràng buộc `unique (heritage_id, category)` trong `rule_entries` ép đúng bất biến quan trọng nhất của Rule Base ngay ở tầng DB.

---

## B1 — `SUPABASE_DB_CONNECTION_STRING` luôn rỗng

**Hiện tượng.** Tên biến trong `.env` và trong `config.py` không khớp:

| Nơi | Tên biến |
|---|---|
| `.env` thực tế | `DATABASE_URL` |
| `backend/.env.example` | `SUPABASE_DB_CONNECTION_STRING` |
| `config.py` đọc | `SUPABASE_DB_CONNECTION_STRING` |

**Bằng chứng.** Chạy từ thư mục gốc repo:

```
SUPABASE_URL                     CÓ GIÁ TRỊ
SUPABASE_SERVICE_ROLE_KEY        CÓ GIÁ TRỊ
SUPABASE_DB_CONNECTION_STRING    >>> RỖNG <<<
```

**Ảnh hưởng.** Supabase client vẫn chạy được vì nó chỉ cần URL + service key. Nhưng mọi thứ cần kết nối Postgres trực tiếp sẽ hỏng — **quan trọng nhất là pgvector cho RAG**, vì `document_chunks.embedding` cần ghi/đọc qua kết nối SQL.

`.env` cũng có `SUPABASE_ANON_KEY` mà `config.py` không đọc.

**Hướng sửa.** Chốt một bộ tên duy nhất cho cả ba nơi. Đề nghị giữ tên của `.env.example` và sửa `.env`, hoặc ngược lại — miễn là thống nhất. Bổ sung `SUPABASE_ANON_KEY` vào `config.py` nếu frontend cần.

---

## B2 — Chạy từ `backend/` thì toàn bộ config rỗng

**Hiện tượng.** `config.py` khai `env_file=".env"` — đường dẫn **tương đối theo thư mục đang đứng**, không phải theo vị trí file.

**Bằng chứng.**

```
cwd = repo root  ->  SUPABASE_URL: CÓ GIÁ TRỊ
cwd = backend/   ->  SUPABASE_URL: RỖNG
                     SUPABASE_SERVICE_ROLE_KEY: RỖNG
                     SUPABASE_DB_CONNECTION_STRING: RỖNG
```

**Ảnh hưởng.** Cách chạy chuẩn của FastAPI là `cd backend && uvicorn app.main:app`. Đúng cách đó thì app khởi động **không có cấu hình nào** và **không báo lỗi gì**. Lỗi chỉ lộ ra khi gọi tới DB.

**Hướng sửa.** Neo `env_file` theo vị trí file thay vì thư mục làm việc:

```python
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent   # backend/
REPO_ROOT = BASE_DIR.parent

model_config = SettingsConfigDict(
    env_file=(REPO_ROOT / ".env", BASE_DIR / ".env"),   # gốc repo, rồi backend/
    env_file_encoding="utf-8",
    extra="ignore",
)
```

---

## B3 — `/health` báo `ok` kể cả khi DB hỏng

**Bằng chứng.**

```
GET /health -> {"status": "ok"}
```

Trả về vô điều kiện, không hề kiểm tra Supabase.

**Ảnh hưởng.** Một endpoint health nói dối còn tệ hơn không có. Lúc demo trước ban giám khảo mà DB rớt thì health vẫn xanh, và ta mất đi công cụ chẩn đoán nhanh duy nhất.

**Hướng sửa.** Cho `/health` thử một truy vấn nhẹ và trả trạng thái thật:

```python
@app.get("/health")
def health_check():
    client = get_supabase_client()
    if client is None:
        return JSONResponse({"status": "degraded", "supabase": "not_configured"}, 503)
    try:
        client.table("sources").select("source_id").limit(1).execute()
        return {"status": "ok", "supabase": "reachable"}
    except Exception as e:
        return JSONResponse({"status": "degraded", "supabase": f"error: {type(e).__name__}"}, 503)
```

---

## B4 — `get_supabase_client()` thất bại im lặng

**Hiện tượng.** Khi thiếu cấu hình, hàm trả `None` thay vì báo lỗi. Mọi nơi gọi phải nhớ tự kiểm tra `None`.

**Ảnh hưởng.** Trái nguyên tắc **default-deny** ở mục 6 spec: *"bất kỳ điều gì không chắc chắn → luôn RESTRICT, không bao giờ mặc định ALLOW"*. Một `None` lọt xuống sâu sẽ gây `AttributeError` ở chỗ cách xa nguyên nhân thật.

**Hướng sửa.** Kiểm tra cấu hình ngay lúc khởi động app và dừng sớm nếu thiếu, thay vì để `None` lan truyền.

**Lưu ý bảo mật kèm theo.** Client đang dùng `SERVICE_ROLE_KEY` — khoá này **bỏ qua toàn bộ Row Level Security**. Chấp nhận được ở backend, nhưng phải đảm bảo nó **không bao giờ** lọt sang Streamlit hay bất kỳ thứ gì chạy phía người dùng. Frontend chỉ được dùng `ANON_KEY`.

---

## D1 — `rule_entries` không có cột lưu `source_note` 🔴

**Đây là lỗ hổng nghiêm trọng nhất.**

**Hiện tượng.**

| | Trường |
|---|---|
| `rule_base.json` có | `heritage_id`, `name`, `origin`, `region`, `cultural_meaning`, `preserve`, `modifiable`, `restricted`, `rule_sources`, **`source_note`** |
| `rule_entries` có cột | `rule_id`, `heritage_id`, `category`, `rule_type`, `source_id` |

**Ảnh hưởng.** `source_note` có ở **13/13** mục và chứa **52 câu trích nguyên văn** đã được kiểm chứng khớp với tài liệu gốc. Import theo schema hiện tại là **mất sạch**.

Không có chúng thì Cultural Passport chỉ hiện được `source_id` trỏ tới tên tài liệu — đúng thứ mà mục 8.3 spec chê là *"AI nói rằng..."*. Toàn bộ định vị **Source-Grounded** của dự án nằm ở đây.

**Hướng sửa.** Xem bản vá SQL ở cuối.

---

## D2 — `sources` mất 11/15 trường 🔴

**Hiện tượng.**

| | Trường |
|---|---|
| `sources.json` có (15) | `file`, `title`, `author`, `year`, `published`, `publisher`, `url`, `doi`, `pages`, `kind`, `tier`, **`rule_basis`**, `has_canonical_pages`, `encoding`, `notes` |
| Bảng `sources` có (5) | `source_id`, `title`, `type`, `reference`, `license` |
| **Không lưu được** | `author`, `year`, `doi`, `published`, `kind`, `tier`, **`rule_basis`**, `has_canonical_pages`, `encoding`, `pages`, `notes` |

**Ảnh hưởng lớn nhất là mất `rule_basis`.** Trường này có ba giá trị và đang cưỡng chế một luật quan trọng (spec mục 19.1.1):

| Giá trị | Được vào `rule_sources`? | Nguồn hiện tại |
|---|---|---|
| `allowed` | Có | SRC001–SRC005 |
| `corroborating_only` | **Không** | SRC006 (không có chú thích nguồn) |
| `forbidden` | **Không** | CTX001 (tài liệu bối cảnh) |

Không có cột này, **DB không ép được** luật *"`CTX001` không bao giờ được viện dẫn làm căn cứ"*. Ràng buộc đó hiện chỉ tồn tại trong script Python `rag/ingest.py`.

**Vấn đề phụ.** `type` chỉ nhận `('academic','museum','other')` trong khi manifest dùng `journal_pdf` / `web_print`. Hai bộ từ vựng khác nhau, cần chốt một.

---

## D3 — `document_chunks` thiếu `locator`, `page`, `section` 🟠

**Hiện tượng.** Cột hiện có: `chunk_id`, `document_id`, `chunk_text`, `embedding`.

Spec mục **8.3.1** (cập nhật 31/08/2026) chốt rằng Evidence định vị nguồn bằng **trích dẫn nguyên văn** (`locator`), còn `page` chỉ dùng cho nguồn có phân trang chính danh — trong corpus hiện tại chỉ có SRC004.

**Ảnh hưởng.** Evidence trả về sẽ không kèm định vị, Cultural Passport không chỉ được đích danh câu nào trong tài liệu nào. Dữ liệu thì đã có sẵn — `data/corpus/*.json` mang `page` cho từng đoạn — nhưng không có chỗ chứa.

**Vấn đề phụ.** Hàm `match_document_chunks` chỉ trả `chunk_id, document_id, chunk_text, similarity`, thiếu metadata để dựng trích dẫn. Nên join sang `documents` + `sources` ngay trong hàm.

---

## D4 — `audit_log` thiếu `rule_base_snapshot` 🟠

**Hiện tượng.** Spec mục 14.2 liệt kê 12 trường. Schema phủ 11:

| Trường spec | Cột DB |
|---|---|
| `timestamp` | `created_at` ✅ |
| `heritage_id` | `heritage_id` ✅ |
| `input_channel` | `input_channel` ✅ |
| `raw_user_intent` | `raw_intent` ✅ |
| `llm_transformations` | `transformation_items` (bảng con) ✅ |
| **`rule_base_snapshot`** | **KHÔNG CÓ CỘT NÀO** ❌ |
| `validator_decisions` | `transformation_items.decision` ✅ |
| `reason` | `transformation_items.reason` ✅ |
| `creative_mode` | `creative_mode` ✅ |
| `controlnet_weight` | `controlnet_weight` ✅ |
| `similarity_score` | `similarity_score` ✅ |
| `seed` | `seed` ✅ |

**Ảnh hưởng.** Rule Base **có thay đổi theo thời gian** — riêng trong phiên rà soát ngày 31/08 đã đổi BT005, BT006, BT010. Không có ảnh chụp tại thời điểm quyết định thì **không tái dựng được** một quyết định cũ dựa trên căn cứ nào.

Với cuộc thi yêu cầu nộp **"lịch sử câu lệnh"** làm minh chứng (xem CLAUDE.md mục 2), đây là mất mát thật chứ không phải lo xa.

---

## Bản vá SQL đề nghị

Chạy sau `db/schema.sql`. Toàn bộ là `ALTER`/`CREATE OR REPLACE`, không phá dữ liệu — hiện cả 7 bảng đang rỗng nên rủi ro bằng 0.

```sql
-- ============================================================
-- D2 — sources: bổ sung metadata thư mục học + rule_basis
-- ============================================================
alter table sources add column if not exists author               text;
alter table sources add column if not exists year                 int;
alter table sources add column if not exists published            date;
alter table sources add column if not exists publisher            text;
alter table sources add column if not exists url                  text;
alter table sources add column if not exists doi                  text;
alter table sources add column if not exists pages                text;
alter table sources add column if not exists kind                 text;
alter table sources add column if not exists tier                 text;
alter table sources add column if not exists has_canonical_pages  boolean default false;
alter table sources add column if not exists encoding             text;
alter table sources add column if not exists notes                text;

alter table sources add column if not exists rule_basis text
  not null default 'allowed'
  check (rule_basis in ('allowed', 'corroborating_only', 'forbidden'));

alter table sources add constraint sources_tier_chk
  check (tier is null or tier in ('A', 'B', 'C'));

-- Bỏ ràng buộc `type` cũ nếu chốt dùng `kind` thay thế:
-- alter table sources drop constraint sources_type_check;

-- ============================================================
-- D2 — ép luật: rule_entries chỉ được trỏ tới nguồn rule_basis='allowed'
-- Đây là ràng buộc mà hiện chỉ script Python đang giữ.
-- ============================================================
create or replace function check_source_allowed_as_rule_basis()
returns trigger language plpgsql as $$
declare v_basis text;
begin
  if new.source_id is null then return new; end if;
  select rule_basis into v_basis from sources where source_id = new.source_id;
  if v_basis is distinct from 'allowed' then
    raise exception
      'source_id % co rule_basis=% nen khong duoc lam can cu cho rule_entries',
      new.source_id, coalesce(v_basis, 'khong ton tai');
  end if;
  return new;
end $$;

drop trigger if exists trg_rule_entries_source_basis on rule_entries;
create trigger trg_rule_entries_source_basis
  before insert or update on rule_entries
  for each row execute function check_source_allowed_as_rule_basis();

-- ============================================================
-- D1 — rule_entries: lưu câu trích nguyên văn làm căn cứ
-- ============================================================
alter table rule_entries add column if not exists source_note text;
alter table rule_entries add column if not exists locator     text;

comment on column rule_entries.source_note is
  'Dien giai can cu, kem cau trich nguyen van dat trong dau nhay don';
comment on column rule_entries.locator is
  'Mot cau trich NGUYEN VAN tu tai lieu nguon, dung hien tren Cultural Passport';

-- ============================================================
-- D3 — document_chunks: định vị trích dẫn theo spec 8.3.1
-- ============================================================
alter table document_chunks add column if not exists src_id   text references sources(source_id);
alter table document_chunks add column if not exists locator  text;
alter table document_chunks add column if not exists section  text;
alter table document_chunks add column if not exists page     int;
alter table document_chunks add column if not exists chunk_index int;

create index if not exists idx_document_chunks_src on document_chunks(src_id);

comment on column document_chunks.page is
  'CHI dien khi sources.has_canonical_pages = true (hien tai chi SRC004)';

-- ============================================================
-- D4 — audit_log: ảnh chụp Rule Base tại thời điểm quyết định
-- ============================================================
alter table audit_log add column if not exists rule_base_snapshot jsonb;

comment on column audit_log.rule_base_snapshot is
  'Ket qua get_rule_base(heritage_id) tai thoi diem generate. Bat buoc theo spec muc 14.2 — '
  'Rule Base thay doi theo thoi gian, khong co anh chup thi khong tai dung duoc quyet dinh cu';

-- ============================================================
-- D3 — match_document_chunks trả kèm metadata trích dẫn
-- ============================================================
create or replace function match_document_chunks(
  query_embedding vector(1024),
  match_count int default 5
)
returns table (
  chunk_id    text,
  src_id      text,
  chunk_text  text,
  locator     text,
  section     text,
  page        int,
  title       text,
  author      text,
  year        int,
  url         text,
  similarity  float
)
language sql stable as $$
  select
    dc.chunk_id, dc.src_id, dc.chunk_text,
    dc.locator, dc.section, dc.page,
    s.title, s.author, s.year, s.url,
    1 - (dc.embedding <=> query_embedding) as similarity
  from document_chunks dc
  left join sources s on s.source_id = dc.src_id
  order by dc.embedding <=> query_embedding
  limit match_count;
$$;
```

---

## Thứ tự đề nghị

| Ưu tiên | Việc | Vì sao trước |
|---|---|---|
| 1 | B1 + B2 (cấu hình) | Chặn pgvector và chặn cách chạy chuẩn của FastAPI |
| 2 | D1 + D2 (schema nguồn) | Phải xong **trước khi import** `rule_base.json`, nếu không import lại mất công |
| 3 | D3 (định vị chunk) | Chặn Cultural Passport, và cần trước khi `rag/embed.py` ghi dữ liệu |
| 4 | D4 (`rule_base_snapshot`) | Cần trước khi bật Audit Log thật |
| 5 | B3 + B4 (health, fail sớm) | Cải thiện vận hành, không chặn ai |

Ưu tiên 2 đáng lưu ý: hiện cả 7 bảng đang **rỗng**, nên sửa schema lúc này không tốn gì. Sửa sau khi đã import 13 heritage item và ~200 chunk thì phải làm lại từ đầu.

---

## Ghi chú thêm

- `backend/app/` thiếu `__init__.py`. Hiện chạy được nhờ namespace package của Python 3.3+, nhưng nên thêm cho tường minh.
- `backend/requirements.txt` chưa có driver Postgres (`psycopg2-binary` hoặc `asyncpg`) — cần khi dùng chuỗi kết nối trực tiếp cho pgvector.
- Trong quá trình rà soát đã cài `fastapi`, `uvicorn`, `pydantic-settings`, `supabase` vào `venv` chung để chạy kiểm tra. Nếu muốn backend có venv riêng thì cần gỡ ra.
