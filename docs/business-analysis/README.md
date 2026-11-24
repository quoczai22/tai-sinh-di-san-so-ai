# Phân tích nghiệp vụ: BPMN và Use Case (bản tối ưu 24/11/2026)

Bộ tài liệu này rà soát và thiết kế lại mô hình quy trình (BPMN 2.0) và Use Case (UML 2.5) của Tái Sinh Di Sản Số,
đối chiếu với mã nguồn bản chung kết. **Không sửa mã nguồn sản phẩm**; mọi thay đổi hệ thống chỉ ở dạng đề xuất (TO-BE).

Quy ước: **AS-IS** là hệ thống đúng như mã đang chạy; **TO-BE** là đề xuất tối ưu. (Trong `docs/finals/` cặp AS-IS/TO-BE
mang nghĩa khác: bản 09/2026 và bản chung kết.)

## Đọc theo thứ tự

| Tệp | Nội dung | Deliverable |
|---|---|---|
| [01_HIEN_TRANG_AS-IS.md](01_HIEN_TRANG_AS-IS.md) | Tài liệu đã khảo sát, tác nhân, quy trình, FR/NFR, luồng dữ liệu, **danh sách vấn đề có mức độ và căn cứ** | 1, 2 |
| [02_BPMN.md](02_BPMN.md) | Bộ BPMN AS-IS và TO-BE, căn cứ trong mã của từng phần tử, lý do từng thay đổi | 3, 4 |
| [03_USE_CASE.md](03_USE_CASE.md) | Use Case AS-IS và TO-BE, đối chiếu với báo cáo cũ, quan hệ include/extend, đặc tả 5 ca chính (16 mục) | 5, 6 |
| [04_TRUY_VET_VA_QUY_TAC.md](04_TRUY_VET_VA_QUY_TAC.md) | Ma trận truy vết BPMN ↔ Use Case ↔ chức năng ↔ API; 22 quy tắc nghiệp vụ có căn cứ, 5 quy tắc đề xuất | 7, 9 |
| [05_TOI_UU_VA_APQC.md](05_TOI_UU_VA_APQC.md) | So sánh AS-IS/TO-BE, Lean, ánh xạ APQC PCF cấp 1–5, danh sách đề xuất, hướng dẫn triển khai | 8, 10, 12 |
| [06_KIEM_DINH.md](06_KIEM_DINH.md) | Kiểm định BPMN (bpmn-js + kiểm tra ngữ nghĩa), kiểm định Use Case, đối chiếu chéo, chất lượng trước/sau | 11 |

## Sơ đồ (`diagrams/`)

| Mã | Tệp | Nội dung |
|---|---|---|
| BP-00 | `BP-00_ban-do-quy-trinh_AS-IS`, `…_TO-BE` | Bản đồ 4 quy trình và 2 kho dữ liệu |
| BP-01 | `BP-01_tao-thiet-ke` | Tạo thiết kế áo dài (AS-IS, giữ nguyên ở TO-BE) |
| BP-01a | `BP-01a_tao-mot-phuong-an` | Tạo một phương án, lặp 4 lần (giữ nguyên ở TO-BE) |
| BP-02 | `BP-02_xem-tai-chinh-sua_AS-IS`, `…_TO-BE` | Xem, tải, chỉnh sửa thiết kế |
| BP-03 | `BP-03_kiem-soat-tham-dinh-xuat-ban_AS-IS`, `…_TO-BE` | Kiểm soát chất lượng, thẩm định, xuất bản |
| BP-04 | `BP-04_tiep-nhan-hien-vat_AS-IS`, `…_TO-BE` | Tiếp nhận hiện vật, quản lý quyền |
| UC | `UC-AS-IS_use-case`, `UC-TO-BE_use-case` | Sơ đồ Use Case |

Mỗi sơ đồ BPMN có `.bpmn` (mở bằng [Camunda Modeler](https://camunda.com/download/modeler/) hoặc kéo thả vào
https://demo.bpmn.io), `.svg` và `.png`. Use Case có `.puml` (PlantUML), `.svg`, `.png`. `stats.json` là số phần tử
đếm từ mô hình; `check_report.json` là kết quả kiểm định.

## Sinh lại sơ đồ

Công cụ ở `tools/` (chỉ dùng cho tài liệu, không thuộc sản phẩm). Cần Python 3.11+ và Playwright (để dựng ảnh).

```powershell
cd docs/business-analysis/tools
python build.py ../diagrams              # sinh .bpmn từ models.py, ghi stats.json
python layoutfix.py ../diagrams --fix    # đặt lại nhãn cho khỏi đè, rồi đo chữ bị chèn (cần mạng để tải bpmn-js)
python layoutfix.py ../diagrams          # đo lại: phải ra "TỔNG 0"
python render.py ../diagrams             # nạp bằng bpmn-js, báo cảnh báo, xuất .svg và .png
python check.py ../diagrams              # kiểm tra ngữ nghĩa, mã thoát 1 nếu có lỗi
python ucgen.py ../diagrams              # sơ đồ Use Case: .svg và .puml
python ucchk.py ../diagrams              # đo chữ bị chèn trong sơ đồ Use Case: phải ra "TỔNG 0"
python svgpng.py ../diagrams/UC-AS-IS_use-case.svg ../diagrams/UC-TO-BE_use-case.svg
```

Sửa quy trình: sửa `tools/models.py` rồi chạy lại năm lệnh đầu. Sửa Use Case: sửa `tools/ucgen.py` rồi chạy ba lệnh cuối.
