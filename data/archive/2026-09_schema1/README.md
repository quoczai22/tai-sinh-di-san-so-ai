# Lưu trữ dữ liệu hiện vật — schema 1.0 (06/09/2026)

Các tệp trong thư mục này **không còn được mã nào đọc**. Giữ lại để minh chứng lịch sử dữ liệu, không xoá.

| Tệp | Trước đây nằm ở | Vì sao lưu trữ |
|---|---|---|
| `heritage_metadata_v1.json` | `data/heritage/metadata.json` | Bản schema 1.0 trước khi chuyển sang 2.0 (Provenance). |
| `metadata_v1.json` | `data/metadata.json` | Bản sao của tệp trên nhưng có thêm URL nguồn. Không mã nào đọc tệp này, nên giao diện và pipeline coi như không có URL. URL đã được gộp vào tệp chuẩn. |
| `items_v1.json` | `data/heritage/items.json` | Gán niên hiệu (Chính Hòa, Vĩnh Thịnh, Cảnh Hưng…) và nguồn bảo tàng cho 6 ảnh **lấy từ trang bán hàng**. Không có căn cứ nào cho các thông tin này. **Không được dùng lại.** |

Tệp chuẩn duy nhất hiện nay: `data/heritage/metadata.json` (schema 2.x). Script chuyển đổi: `scripts/08_migrate_heritage_metadata_v2.py`.
