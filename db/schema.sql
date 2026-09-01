-- ============================================================
-- TÁI SINH DI SẢN SỐ — DATABASE SCHEMA (Supabase/Postgres)
-- Dựa trên ERD đã thống nhất (7 bảng) + 2 bổ sung nhỏ:
--   1. audit_log.raw_intent (câu gốc trước khi Planner tách)
--   2. document_chunks.embedding chốt vector(1024) cho BGE-M3
-- ============================================================

-- 0. Extension bắt buộc
create extension if not exists vector;
create extension if not exists pgcrypto; -- cho gen_random_uuid() nếu cần

-- ============================================================
-- 1. SOURCES — dùng chung cho rule justification lẫn tài liệu RAG
-- ============================================================
create table if not exists sources (
  source_id   text primary key,
  title       text not null,
  type        text not null check (type in ('academic', 'museum', 'other')),
  reference   text,           -- ví dụ: link Google Arts & Culture, tên sách, trang
  license     text,           -- ví dụ: "public domain", "CC-BY", "xin phép sử dụng"
  created_at  timestamptz default now()
);

-- ============================================================
-- 2. HERITAGE_ITEMS — bảng trung tâm, 10-15 mẫu gốm Bát Tràng
-- ============================================================
create table if not exists heritage_items (
  heritage_id       text primary key,      -- ví dụ: 'BT001'
  name              text not null,
  origin            text,
  region            text,
  cultural_meaning  text,
  image_path        text,                  -- path trong Supabase Storage
  license           text,
  created_at        timestamptz default now()
);

-- ============================================================
-- 3. RULE_ENTRIES — mỗi category = 1 dòng, truy ngược được nguồn
-- ============================================================
create table if not exists rule_entries (
  rule_id      text primary key,
  heritage_id  text not null references heritage_items(heritage_id) on delete cascade,
  category     text not null check (category in (
                  'background', 'color_palette', 'composition_layout',
                  'core_motif', 'symbolic_element', 'product_context',
                  'material_texture', 'other_unclassified'
               )),
  rule_type    text not null check (rule_type in ('preserve', 'modifiable', 'restricted')),
  source_id    text references sources(source_id),
  created_at   timestamptz default now(),
  -- Mỗi heritage_item chỉ có 1 rule cho mỗi category — tránh mâu thuẫn logic
  unique (heritage_id, category)
);

create index if not exists idx_rule_entries_heritage on rule_entries(heritage_id);

-- ============================================================
-- 4. DOCUMENTS — tài liệu văn hóa dài dùng cho RAG (Evidence)
-- ============================================================
create table if not exists documents (
  document_id   text primary key,
  source_id     text references sources(source_id),
  title         text,
  content_path  text,     -- path file gốc (PDF/txt) trong Storage
  created_at    timestamptz default now()
);

-- ============================================================
-- 5. DOCUMENT_CHUNKS — chunk + embedding cho vector search (pgvector)
--    BGE-M3 output = 1024 chiều
-- ============================================================
create table if not exists document_chunks (
  chunk_id     text primary key,
  document_id  text not null references documents(document_id) on delete cascade,
  chunk_text   text not null,
  embedding    vector(1024),
  created_at   timestamptz default now()
);

-- Index HNSW cho tìm kiếm cosine similarity nhanh (pgvector >= 0.5.0)
-- Nếu bản pgvector cũ hơn không hỗ trợ hnsw, dùng ivfflat thay thế (dòng comment dưới).
create index if not exists idx_document_chunks_embedding
  on document_chunks using hnsw (embedding vector_cosine_ops);
-- create index if not exists idx_document_chunks_embedding
--   on document_chunks using ivfflat (embedding vector_cosine_ops) with (lists = 100);

-- ============================================================
-- 6. AUDIT_LOG — một dòng cho mỗi lượt generate
--    (đã bổ sung raw_intent so với ERD gốc)
-- ============================================================
create table if not exists audit_log (
  request_id        text primary key,
  heritage_id       text references heritage_items(heritage_id),
  created_at        timestamptz default now(),
  input_channel     text check (input_channel in ('checkbox', 'free_text')),
  raw_intent        text,              -- câu gốc người dùng gõ (nếu free_text); NULL nếu checkbox
  creative_mode     text check (creative_mode in ('preserve', 'reimagine')),
  controlnet_weight float,
  similarity_score  float,
  seed              int,
  output_path       text               -- path ảnh output trong Storage
);

create index if not exists idx_audit_log_heritage on audit_log(heritage_id);

-- ============================================================
-- 7. TRANSFORMATION_ITEMS — bảng con của AUDIT_LOG
--    mỗi transformation item độc lập, có decision + reason riêng
-- ============================================================
create table if not exists transformation_items (
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

create index if not exists idx_transformation_items_request on transformation_items(request_id);

-- ============================================================
-- HELPER FUNCTION — get_rule_base(heritage_id)
-- Trả về đúng JSON schema mà LLM Planner/Validator cần
-- (khớp mục 7.2 MVP Spec: preserve/modifiable/restricted + rule_sources)
-- ============================================================
create or replace function get_rule_base(p_heritage_id text)
returns jsonb
language sql
stable
as $$
  select jsonb_build_object(
    'heritage_id', p_heritage_id,
    'preserve',    coalesce((select jsonb_agg(category) from rule_entries
                              where heritage_id = p_heritage_id and rule_type = 'preserve'), '[]'::jsonb),
    'modifiable',  coalesce((select jsonb_agg(category) from rule_entries
                              where heritage_id = p_heritage_id and rule_type = 'modifiable'), '[]'::jsonb),
    'restricted',  coalesce((select jsonb_agg(category) from rule_entries
                              where heritage_id = p_heritage_id and rule_type = 'restricted'), '[]'::jsonb),
    'rule_sources', coalesce((select jsonb_object_agg(category, source_id) from rule_entries
                               where heritage_id = p_heritage_id and source_id is not null), '{}'::jsonb)
  );
$$;

-- Cách gọi từ backend (FastAPI/Supabase client):
--   select get_rule_base('BT001');
-- Kết quả trả về đúng format Validator cần, không cần code Python join thủ công.

-- ============================================================
-- HELPER FUNCTION — match_document_chunks(query_embedding, heritage liên quan, top_k)
-- Dùng cho Evidence retrieval (RAG thật, bắt buộc vector search)
-- ============================================================
create or replace function match_document_chunks(
  query_embedding vector(1024),
  match_count int default 5
)
returns table (
  chunk_id text,
  document_id text,
  chunk_text text,
  similarity float
)
language sql
stable
as $$
  select
    dc.chunk_id,
    dc.document_id,
    dc.chunk_text,
    1 - (dc.embedding <=> query_embedding) as similarity
  from document_chunks dc
  order by dc.embedding <=> query_embedding
  limit match_count;
$$;