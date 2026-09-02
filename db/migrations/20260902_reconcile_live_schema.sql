-- ============================================================
-- TÁI SINH DI SẢN SỐ — DATABASE MIGRATION (Idempotent)
-- File: db/migrations/20260902_reconcile_live_schema.sql
-- Mục đích: Tái lập/đồng bộ cấu trúc live DB từ schema cũ (D1-D4).
-- Đặc tính: Idempotent (chạy lặp lại an toàn), có Preflight check 7 bảng,
--           không DROP table/column, không DELETE/TRUNCATE,
--           bảo tồn sources.type, backfill và kiểm tra FK/NOT NULL an toàn.
-- ============================================================

-- 0. EXTENSIONS
create extension if not exists vector;
create extension if not exists pgcrypto;

-- ============================================================
-- PREFLIGHT CHECK — Kiểm tra sự tồn tại của đủ 7 bảng lõi
-- Dừng ngay và raise exception nếu thiếu bất kỳ bảng nào trước khi mutate.
-- ============================================================
do $$
declare
  v_missing text[];
begin
  select array_agg(t.table_name)
  into v_missing
  from (
    select unnest(array[
      'sources',
      'heritage_items',
      'rule_entries',
      'documents',
      'document_chunks',
      'audit_log',
      'transformation_items'
    ]) as table_name
  ) t
  where not exists (
    select 1
    from information_schema.tables
    where table_schema = 'public' and table_name = t.table_name
  );

  if v_missing is not null and array_length(v_missing, 1) > 0 then
    raise exception
      'Preflight check failed: Các bảng lõi sau chưa tồn tại trong schema public: %. Migration dừng lại trước khi thực hiện bất kỳ lệnh mutate nào.',
      array_to_string(v_missing, ', ');
  end if;
end;
$$;

-- ============================================================
-- 1. BẢNG SOURCES (D2)
--    Bổ sung metadata nguồn và ràng buộc rule_basis.
--    Giữ nguyên cột 'type' cũ nếu có để đảm bảo tương thích ngược.
-- ============================================================
alter table sources
  add column if not exists author text,
  add column if not exists year int,
  add column if not exists published date,
  add column if not exists publisher text,
  add column if not exists url text,
  add column if not exists doi text,
  add column if not exists pages text,
  add column if not exists kind text,
  add column if not exists tier text check (tier in ('A', 'B', 'C')),
  add column if not exists has_canonical_pages boolean not null default false,
  add column if not exists encoding text,
  add column if not exists notes text,
  add column if not exists license text,
  add column if not exists rule_basis text not null default 'allowed'
    check (rule_basis in ('allowed', 'corroborating_only', 'forbidden'));

comment on column sources.rule_basis is
  'allowed = duoc vien dan trong rule_sources; corroborating_only = chi nhac trong source_note, '
  'khong duoc dung mot minh; forbidden = khong bao gio duoc vien dan (vd: tai lieu boi canh CTX*)';

-- ============================================================
-- 2. BẢNG HERITAGE_ITEMS
-- ============================================================
create table if not exists heritage_items (
  heritage_id       text primary key,
  name              text not null,
  origin            text,
  region            text,
  cultural_meaning  text,
  image_path        text,
  license           text,
  created_at        timestamptz default now()
);

-- ============================================================
-- 3. BẢNG RULE_ENTRIES (D1, D2)
--    Bổ sung source_note và locator (trích dẫn nguyên văn)
--    Trigger ép luật: chỉ source có rule_basis = 'allowed' mới làm căn cứ
-- ============================================================
alter table rule_entries
  add column if not exists source_note text,
  add column if not exists locator text;

create index if not exists idx_rule_entries_heritage on rule_entries(heritage_id);

create or replace function check_source_allowed_as_rule_basis()
returns trigger language plpgsql as $$
declare
  v_basis text;
begin
  if new.source_id is null then
    return new;
  end if;

  select rule_basis into v_basis from sources where source_id = new.source_id;
  if v_basis is distinct from 'allowed' then
    raise exception
      'source_id % co rule_basis=% nen khong duoc lam can cu cho rule_entries',
      new.source_id, coalesce(v_basis, 'khong ton tai');
  end if;

  return new;
end;
$$;

drop trigger if exists trg_rule_entries_source_basis on rule_entries;
create trigger trg_rule_entries_source_basis
  before insert or update on rule_entries
  for each row execute function check_source_allowed_as_rule_basis();

-- ============================================================
-- 4. BẢNG DOCUMENTS
-- ============================================================
create table if not exists documents (
  document_id   text primary key,
  source_id     text references sources(source_id),
  title         text,
  content_path  text,
  created_at    timestamptz default now()
);

-- ============================================================
-- 5. BẢNG DOCUMENT_CHUNKS (D3)
--    Bổ sung src_id, chunk_index, locator, section, page.
--    Quy trình xử lý an toàn:
--    1) Thêm nullable src_id nếu chưa có
--    2) Kiểm tra & tạo FK tới sources(source_id) nếu chưa tồn tại
--    3) Backfill src_id từ documents.source_id
--    4) Kiểm tra số dòng src_id IS NULL
--    5) Chỉ set NOT NULL khi count NULL = 0; nếu còn NULL thì raise exception
-- ============================================================
alter table document_chunks
  add column if not exists src_id text,
  add column if not exists chunk_index int,
  add column if not exists locator text,
  add column if not exists section text,
  add column if not exists page int;

-- Đảm bảo Foreign Key tới sources(source_id) tồn tại
do $$
begin
  if not exists (
    select 1
    from pg_constraint c
    join pg_class t on c.conrelid = t.oid
    join pg_namespace n on t.relnamespace = n.oid
    where n.nspname = 'public'
      and t.relname = 'document_chunks'
      and c.contype = 'f'
      and pg_get_constraintdef(c.oid) like '%FOREIGN KEY (src_id) REFERENCES sources(source_id)%'
  ) then
    alter table document_chunks
      add constraint document_chunks_src_id_fkey
      foreign key (src_id) references sources(source_id);
  end if;
end;
$$;

-- Backfill src_id từ documents nếu src_id đang NULL
update document_chunks dc
set src_id = d.source_id
from documents d
where dc.document_id = d.document_id and dc.src_id is null;

-- Kiểm tra và chỉ đặt NOT NULL khi hoàn toàn an toàn (count NULL = 0)
do $$
declare
  v_null_count int;
begin
  select count(*) into v_null_count from document_chunks where src_id is null;
  if v_null_count > 0 then
    raise exception
      'Migration dừng lại: còn % dòng trong document_chunks có src_id IS NULL, không thể đặt NOT NULL an toàn.',
      v_null_count;
  else
    alter table document_chunks alter column src_id set not null;
  end if;
end;
$$;

create index if not exists idx_document_chunks_src on document_chunks(src_id);

create index if not exists idx_document_chunks_embedding
  on document_chunks using hnsw (embedding vector_cosine_ops);

comment on column document_chunks.page is
  'Chi dien khi sources.has_canonical_pages = true (hien tai chi SRC004)';

-- ============================================================
-- 6. BẢNG AUDIT_LOG (D4)
--    Bổ sung rule_base_snapshot (jsonb)
-- ============================================================
alter table audit_log
  add column if not exists rule_base_snapshot jsonb;

create index if not exists idx_audit_log_heritage on audit_log(heritage_id);

comment on column audit_log.rule_base_snapshot is
  'Ket qua get_rule_base(heritage_id) tai thoi diem generate. Rule Base thay doi theo thoi '
  'gian, khong co anh chup thi khong tai dung duoc quyet dinh cu dua tren can cu nao';

-- ============================================================
-- 7. BẢNG TRANSFORMATION_ITEMS
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
-- 8. ROW LEVEL SECURITY (RLS)
--    Bật RLS trên cả 7 bảng để bảo vệ dữ liệu khi Supabase expose REST API
-- ============================================================
alter table sources               enable row level security;
alter table heritage_items        enable row level security;
alter table rule_entries          enable row level security;
alter table documents             enable row level security;
alter table document_chunks       enable row level security;
alter table audit_log             enable row level security;
alter table transformation_items  enable row level security;

-- ============================================================
-- 9. HELPER FUNCTION — get_rule_base (Fail-closed & Full Metadata)
-- ============================================================
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
    return null;  -- Fail-closed: Mẫu không tồn tại trả NULL, tránh lỗi fail-open
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
-- 10. HELPER FUNCTION — match_document_chunks (Citation Metadata)
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
