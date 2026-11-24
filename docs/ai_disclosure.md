# Khai báo công cụ AI đã dùng

Tài liệu này trả lời yêu cầu 3 của ban tổ chức về nhãn nội dung có hỗ trợ AI và truy vết. Mỗi mục ghi rõ: công cụ nào, làm việc gì, kết quả nằm ở đâu. Mục nào chưa kiểm chứng thì ghi `[CẦN NHÓM ĐIỀN]`, không đoán.

Ngày soạn: 22/11/2026. Mã nguồn tham chiếu: nhánh `test`.

## 1. Mô hình AI chạy trong hệ thống

| Công cụ | Việc làm | Mã định danh trong mã nguồn | Dùng ở đâu |
|---|---|---|---|
| Stable Diffusion 1.5 | Sinh hoa văn phẳng (giai đoạn 1), sinh áo dài nền, hoàn thiện ảnh (polish) | `stable-diffusion-v1-5/stable-diffusion-v1-5` | `tsds/generation/stable_diffusion.py` |
| ControlNet Canny v1.1 | Giữ nét viền của hiện vật khi sinh hoa văn | `lllyasviel/control_v11p_sd15_canny` | `tsds/generation/stable_diffusion.py`, `tsds/generation/pattern/controlnet.py` |
| LoRA dáng áo dài (nhóm huấn luyện) | Giúp Stable Diffusion sinh áo dài nền đúng dáng | `data/lora/aodai_r16_512/` | `tsds/generation/garment/garment_lora.py` |
| CLIP ViT-B/32 | Chấm điểm để xếp hạng các bố cục hoa văn trên áo | `openai/clip-vit-base-patch32` | `tsds/generation/garment/layout_select.py` |
| SAM (Segment Anything, bản base) | Tách vùng áo và tách phần tử hoa văn khỏi ảnh | `facebook/sam-vit-base` | `tsds/generation/garment/garment_sam.py`, `tsds/generation/pattern/elements.py` |

Giấy phép của từng mô hình: `[CẦN NHÓM ĐIỀN: đối chiếu trên trang mô hình tương ứng ở Hugging Face trước khi nộp]`. Riêng LoRA xem mục 3.

**Phần không do AI:** ghép hoa văn lên áo theo bố cục, khớp màu, khoá họa tiết sau polish (`tsds/core/pattern_lock.py`) và các phép đo của cổng chất lượng đều là thuật toán tất định (OpenCV, NumPy), không gọi mô hình sinh ảnh.

## 2. Nội dung do AI tạo ra

| Nội dung | Do AI tạo thế nào | Nhãn và truy vết |
|---|---|---|
| Hoa văn phẳng | Stable Diffusion cộng ControlNet vẽ từ ảnh hiện vật | Passport ghi bước `generate_pattern`, người thực hiện là `ai` |
| Áo dài nền | Stable Diffusion cộng LoRA sinh mới mỗi lượt | Passport ghi bước `generate_garment`, kèm seed và mã băm |
| Ảnh thiết kế cuối | Polish bằng Stable Diffusion img2img chỉ trong vùng áo | Bước `polish` và phiên bản `ai_generated` trong Passport |
| Mô tả hoa văn bằng tiếng Anh dùng làm prompt | Do nhóm viết tay, hoặc do mô hình thị giác (Gemini, qua `scripts/data_prep/describe_heritage.py`) soạn bản nháp | Passport ghi bước `describe_motif`, người thực hiện là `ai` hoặc `human` tuỳ nguồn |
| Câu chữ mô tả hiện vật tiếng Việt trong `data/heritage/metadata.json` | Nhóm biên soạn từ quan sát ảnh, trợ lý Claude hỗ trợ soạn câu chữ. Bản nháp, nhóm đã ghi cần rà soát | Trường `visual_summary_origin` trong metadata |
| Một phần mã nguồn và tài liệu của dự án | Nhóm làm với sự hỗ trợ của trợ lý lập trình AI (Claude Code) | Lịch sử git; nhóm chịu trách nhiệm kiểm tra |

Mô hình Gemini mặc định trong script là `gemini-3.7-flash`, đổi bằng biến `GEMINI_MODEL` trong `.env`. Khoá API không đưa vào repo.

## 3. Dữ liệu huấn luyện LoRA

- Nguồn: 226 ảnh đã lọc từ bộ dữ liệu VietFashion, giấy phép **CC BY-NC 4.0** (chỉ dùng phi thương mại).
- Tác giả bộ dữ liệu đã đồng ý bằng email cho nhóm dùng. `[CẦN NHÓM ĐIỀN: lưu thư trả lời vào hồ sơ minh chứng]`.
- Hệ quả: trọng số LoRA **không được dùng cho mục đích thương mại**. Hệ thống chỉ dùng cho dự thi và thử nghiệm.
- Trích dẫn: Cao, Bui, Vo, Tran, Le. VietFashion: Benchmarking Sketch-Text Composed Image Retrieval for Cultural Outfits. ICMR 2026. doi:10.1145/3805622.3810590.
- Ảnh VietFashion không nằm trong repo (`data/raw/`, không commit). Chi tiết: `data/lora/README.md`.

## 4. Bộ lọc an toàn của Stable Diffusion đã tắt (quyết định có chủ đích)

**Việc đã làm:** trong `tsds/generation/stable_diffusion.py`, tham số `safety_checker` đặt là `None`.

**Lý do:** theo ghi chú trong mã, bộ lọc này báo nhầm (false positive) trên hoa văn có yếu tố tôn giáo, nên trả về ảnh đen. Hoa văn gốm Bát Tràng có nhiều họa tiết như vậy.

**Biện pháp thay thế:**
1. Người dùng không nhập chữ tự do. API `/generate` chỉ nhận mã hiện vật (`heritage_id`) và seed (`tsds/api/main.py`, lớp `GenerateRequest`). Prompt luôn lắp từ mô tả của 6 hiện vật đã duyệt.
2. Mọi thiết kế đi qua cổng chất lượng G2 và G3 trước khi trả về; thiết kế lỗi bị loại hoặc thay bằng bản ghép thô.
3. Mọi thiết kế có trạng thái duyệt trong Passport (`chờ chuyên gia thẩm định`, `có cảnh báo`, `không đạt`...). Chưa thiết kế nào được ghi là đã thẩm định.

**Hạn chế:** biện pháp 1 chỉ đúng khi người dùng đi qua giao diện và API hiện tại. Nếu sau này thêm ô nhập prompt tự do thì phải bật lại bộ lọc hoặc thêm bước kiểm duyệt khác.

## 5. Nhãn "có hỗ trợ AI" và truy vết

- **Nhãn nhìn thấy:** khi xuất ảnh qua `GET /passports/{id}/export`, mép dưới ảnh ghi "Thiết kế hỗ trợ bởi AI" cùng mã Passport (`tsds/provenance/labeling.py`).
- **Siêu dữ liệu trong file PNG:** `ai_generated`, `ai_label`, `passport_id`, mã băm thiết kế, tên hiện vật, ghi công, cờ cảnh báo quyền.
- **Design Passport:** hồ sơ đi kèm mỗi thiết kế, gồm chuỗi bước từ ảnh nguồn đến thành phẩm, mỗi bước có người thực hiện (`ai`, `system`, `human`), tham số, seed và mã băm SHA-256. Lệnh kiểm tra toàn vẹn: `tsds/provenance/passport.py::verify`. Bước sửa tay của con người được ghi riêng và phải qua lại cổng G3.
- **Chưa làm:** chữ ký chuẩn C2PA (cần chứng thư số). Ghi ở mục hướng phát triển của hồ sơ.

## 6. Giới hạn cần nêu trung thực

- Chưa có người am hiểu di sản hoặc thiết kế thẩm định mẫu. Có 28 phiếu chấm mù của người quan tâm, nhưng họ ít đồng thuận (alpha 0,03), nên chưa dùng điểm để kết luận. Xem `docs/evidence/README.md`.
- Ghi công nguồn ảnh: 6 hiện vật thuộc bộ LR3D-CULT2 (CC BY 4.0, DOI 10.17632/jr23fnrvx2.1). Nhóm chưa xác minh riêng nguồn của từng vật (một phần mô hình trong bộ có thể lấy từ Sketchfab theo giấy phép học thuật). Chi tiết: `docs/DANH_MUC_NGUON_HIEN_VAT.md`.
- Căn cứ pháp lý về dán nhãn nội dung AI: `[CẦN NHÓM ĐIỀN: trích văn bản gốc đã đối chiếu, không trích từ bài tổng hợp]`.
