-- ============================================================
-- TÁI SINH DI SẢN SỐ — DATABASE SCHEMA (Supabase/Postgres)
-- Phiên bản: 02 — viết lại hoàn toàn theo backend_review_20260901.md
-- Áp dụng đủ D1, D2, D3, D4. Không dùng ALTER — 7 bảng đang rỗng
-- nên viết lại CREATE TABLE trực tiếp là an toàn và sạch hơn.
-- ============================================================

create extension if not exists vector;
create extension if not exists pgcrypto;

-- ============================================================
-- 1. SOURCES — dùng chung cho rule justification lẫn tài liệu RAG
--    Đã mở rộng đủ 15 trường theo data/sources.json (mục 19.1 spec)
-- ============================================================
create table sources (
  source_id           text primary key,        -- SRC001..SRC00N hoặc CTX001..
  title               text not null,
  author              text,
  year                int,
  published           date,
  publisher           text,
  url                 text,
  doi                 text,
  pages               text,                     -- dạng "104-114", chỉ mang tính mô tả
  kind                text,                     -- 'journal_pdf' | 'web_print' | 'museum_exhibit' | ...
  tier                text check (tier in ('A', 'B', 'C')),
  has_canonical_pages boolean not null default false,
  encoding            text,
  notes               text,
  license             text,

  -- Trường quan trọng nhất: quyết định nguồn có được dùng làm căn cứ rule không
  rule_basis          text not null default 'allowed'
                        check (rule_basis in ('allowed', 'corroborating_only', 'forbidden')),

  created_at          timestamptz default now()
);

comment on column sources.rule_basis is
  'allowed = duoc vien dan trong rule_sources; corroborating_only = chi nhac trong source_note, '
  'khong duoc dung mot minh; forbidden = khong bao gio duoc vien dan (vd: tai lieu boi canh CTX*)';

-- ============================================================
-- 2. HERITAGE_ITEMS — bảng trung tâm, 10-15 mẫu gốm Bát Tràng
-- ============================================================
create table heritage_items (
  heritage_id       text primary key,
  name              text not null,
  origin            text,
  region            text,
  cultural_meaning  text,
  image_path        text,
  license            text,
  created_at        timestamptz default now()
);

-- ============================================================
-- 3. RULE_ENTRIES — mỗi category = 1 dòng, kèm câu trích nguyên văn
--    Đã bổ sung source_note + locator (D1 — lỗ hổng nghiêm trọng nhất)
-- ============================================================
create table rule_entries (
  rule_id      text primary key,
  heritage_id  text not null references heritage_items(heritage_id) on delete cascade,
  category     text not null check (category in (
                  'background', 'color_palette', 'composition_layout',
                  'core_motif', 'symbolic_element', 'product_context',
                  'material_texture', 'other_unclassified'
               )),
  rule_type    text not null check (rule_type in ('preserve', 'modifiable', 'restricted')),
  source_id    text references sources(source_id),

  -- D1: bắt buộc để không mất 52 câu trích đã kiểm chứng
  source_note  text,   -- diễn giải căn cứ, kèm câu trích nguyên văn đặt trong dấu nháy đơn
  locator      text,   -- một câu trích NGUYÊN VĂN từ tài liệu nguồn, hiển thị trên Cultural Passport

  created_at   timestamptz default now(),
  unique (heritage_id, category)
);

create index idx_rule_entries_heritage on rule_entries(heritage_id);

-- Ép luật D2: rule_entries chỉ được trỏ tới nguồn có rule_basis = 'allowed'
-- Đây là ràng buộc quan trọng — trước đây chỉ tồn tại trong script Python rag/ingest.py
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

create trigger trg_rule_entries_source_basis
  before insert or update on rule_entries
  for each row execute function check_source_allowed_as_rule_basis();

-- ============================================================
-- 4. DOCUMENTS — tài liệu văn hóa dài dùng cho RAG (Evidence)
-- ============================================================
create table documents (
  document_id   text primary key,
  source_id     text references sources(source_id),
  title         text,
  content_path  text,
  created_at    timestamptz default now()
);

-- ============================================================
-- 5. DOCUMENT_CHUNKS — chunk + embedding cho vector search (pgvector)
--    Đã bổ sung src_id, locator, section, page, chunk_index (D3)
-- ============================================================
create table document_chunks (
  chunk_id     text primary key,
  document_id  text not null references documents(document_id) on delete cascade,
  src_id       text not null references sources(source_id),   -- truy vết trực tiếp, không cần join qua documents
  chunk_index  int,                                            -- thứ tự chunk trong tài liệu
  chunk_text   text not null,

  -- Định vị trích dẫn theo spec 8.3.1 (quyết định 31/08/2026)
  locator      text,   -- câu trích NGUYÊN VĂN, dùng làm định vị chính
  section      text,   -- mục đánh số nếu tài liệu có (vd "2.6. Bình vôi")
  page         int,    -- CHỈ điền khi sources.has_canonical_pages = true (hiện tại chỉ SRC004)

  embedding    vector(1024),   -- BGE-M3, 1024 chiều
  created_at   timestamptz default now()
);

create index idx_document_chunks_src on document_chunks(src_id);

create index idx_document_chunks_embedding
  on document_chunks using hnsw (embedding vector_cosine_ops);
-- Nếu bản pgvector không hỗ trợ hnsw, dùng thay:
-- create index idx_document_chunks_embedding
--   on document_chunks using ivfflat (embedding vector_cosine_ops) with (lists = 100);

comment on column document_chunks.page is
  'Chi dien khi sources.has_canonical_pages = true (hien tai chi SRC004)';

-- ============================================================
-- 6. AUDIT_LOG — một dòng cho mỗi lượt generate
--    Đã bổ sung rule_base_snapshot (D4)
-- ============================================================
create table audit_log (
  request_id          text primary key,
  heritage_id         text references heritage_items(heritage_id),
  created_at          timestamptz default now(),
  input_channel       text check (input_channel in ('checkbox', 'free_text')),
  raw_intent          text,
  creative_mode       text check (creative_mode in ('preserve', 'reimagine')),
  controlnet_weight   float,
  similarity_score    float,
  seed                int,
  output_path         text,

  -- D4: ảnh chụp Rule Base tại thời điểm quyết định — bắt buộc theo spec mục 14.2
  rule_base_snapshot  jsonb
);

comment on column audit_log.rule_base_snapshot is
  'Ket qua get_rule_base(heritage_id) tai thoi diem generate. Rule Base thay doi theo thoi '
  'gian, khong co anh chup thi khong tai dung duoc quyet dinh cu dua tren can cu nao';

create index idx_audit_log_heritage on audit_log(heritage_id);

-- ============================================================
-- 7. TRANSFORMATION_ITEMS — bảng con của AUDIT_LOG
-- ============================================================
create table transformation_items (
  item_id             text primary key,
  request_id          text not null references audit_log(request_id) on delete cascade,
  raw_phrase          text,
  label               text check (label in (
                        'background', 'color_palette', 'composition_layout',
                        'core_motif', 'symbolic_element', 'product_context',
                        'material_texture', 'other_unclassified'
                     )),
  consistency_status  text check (consistency_status in ('consistent', 'inconsistent')),
  decision            text check (decision in ('ALLOW', 'RESTRICT', 'BLOCK')),
  reason              text
);

create index idx_transformation_items_request on transformation_items(request_id);

-- ============================================================
-- ROW LEVEL SECURITY — bắt buộc vì Supabase expose bảng qua REST API.
-- MVP chưa có Auth → bật RLS, KHÔNG tạo policy cho anon/authenticated.
-- Backend dùng service_role key sẽ tự bypass RLS.
-- ============================================================
alter table sources               enable row level security;
alter table heritage_items        enable row level security;
alter table rule_entries          enable row level security;
alter table documents             enable row level security;
alter table document_chunks       enable row level security;
alter table audit_log             enable row level security;
alter table transformation_items  enable row level security;

-- ============================================================
-- HELPER FUNCTION — get_rule_base(heritage_id)
-- Trả JSON cho LLM Planner/Validator + đủ dữ liệu cho Cultural Passport
-- (đã bổ sung source_notes/locators so với bản đầu, để không phải
-- query rời rạc thêm lần nữa khi build UI trích dẫn)
-- ============================================================
-- FAIL-CLOSED: heritage_id không tồn tại → trả NULL (không phải object rỗng).
-- Lý do: object rỗng hợp lệ ("preserve": []) và NULL ("không biết mẫu này")
-- mang 2 ý nghĩa khác nhau. Nếu trả object rỗng cho mẫu không tồn tại,
-- Validator đọc vào sẽ hiểu nhầm "không có gì cần bảo vệ" -> ALLOW mọi thứ,
-- vi phạm nguyên tắc default-deny ở spec mục 6. Backend PHẢI coi NULL là
-- lỗi/chặn request, không được coi NULL tương đương object rỗng.
create or replace function get_rule_base(p_heritage_id text)
returns jsonb
language plpgsql
stable
as $$
declare
  v_exists boolean;
begin
  select exists(select 1 from heritage_items where heritage_id = p_heritage_id) into v_exists;
 
  if not v_exists then
    return null;  -- KHÔNG trả object rỗng — bắt buộc backend fail-closed
  end if;
 
  return jsonb_build_object(
    'heritage_id', p_heritage_id,
    'preserve',     coalesce((select jsonb_agg(category) from rule_entries
                               where heritage_id = p_heritage_id and rule_type = 'preserve'), '[]'::jsonb),
    'modifiable',   coalesce((select jsonb_agg(category) from rule_entries
                               where heritage_id = p_heritage_id and rule_type = 'modifiable'), '[]'::jsonb),
    'restricted',   coalesce((select jsonb_agg(category) from rule_entries
                               where heritage_id = p_heritage_id and rule_type = 'restricted'), '[]'::jsonb),
    'rule_sources', coalesce((select jsonb_object_agg(category, source_id) from rule_entries
                               where heritage_id = p_heritage_id and source_id is not null), '{}'::jsonb),
    'source_notes', coalesce((select jsonb_object_agg(category, source_note) from rule_entries
                               where heritage_id = p_heritage_id and source_note is not null), '{}'::jsonb),
    'locators',     coalesce((select jsonb_object_agg(category, locator) from rule_entries
                               where heritage_id = p_heritage_id and locator is not null), '{}'::jsonb)
  );
end;
$$;

-- ============================================================
-- HELPER FUNCTION — match_document_chunks
-- Trả kèm đủ metadata trích dẫn (locator/section/page + tên tác giả/năm/url)
-- để Cultural Passport dựng câu trích dẫn ngay, không cần join thêm lần nữa.
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
language sql
stable
as $$
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

select count(*) from document_chunks;                    -- 198
select count(*) from document_chunks where embedding is not null;  -- 198
select chunk_id, src_id, section, page, left(locator,60) from document_chunks limit 5;
select * from get_rule_base('BT001');

-- DROP FUNCTION match_document_chunks(vector,integer)
-- drop table if exists transformation_items, audit_log, document_chunks,
--                      documents, rule_entries, heritage_items, sources cascade;

