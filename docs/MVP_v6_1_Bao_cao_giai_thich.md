# Báo cáo giải thích MVP v6.1 — Tái sinh Di sản Số

## 1. Tóm tắt một câu

MVP mới là một pipeline **Generate-and-Curate**: người dùng chọn một hiện vật gốm Bát Tràng, bấm một nút, hệ thống sinh một bộ bốn thiết kế áo dài khác nhau, rồi người dùng chọn mẫu ưng ý và xem Design Passport.

Sản phẩm không còn cố gắng để người dùng điều khiển “mức sáng tạo”. Giá trị chính chuyển sang khả năng sinh nhiều phương án có kiểm soát, có đo lường và có thông tin minh bạch để người dùng curate.

## 2. Vì sao MVP thay đổi

MVP cũ đưa ảnh gốm vào ControlNet đồng thời yêu cầu mô hình vẽ áo dài. Hai tín hiệu hình học mâu thuẫn: ảnh gốm chứa dáng bình/lọ, còn prompt yêu cầu dáng áo dài. Kết quả đo được cho thấy:

| Weight | Xác suất sinh đúng áo dài |
| ---: | ---: |
| 0,85 | 0,000 |
| 0,65 | 0,000 |
| 0,45 | 0,016 |
| 0,25 | 1,000 |

Vì vậy chỉ chỉnh weight không giải quyết được xung đột. v6.1 tách thành hai giai đoạn: trước hết sinh hoa văn phẳng, sau đó ghép hoa văn lên ảnh áo dài bằng xử lý tất định.

## 3. Phạm vi cố định

- Di sản: gốm Bát Tràng.
- Dataset MVP: **6 hiện vật**.
- Sản phẩm duy nhất: áo dài Việt Nam.
- Sinh ảnh: Stable Diffusion 1.5 + ControlNet trên GPU local.
- Bốn weight `0.85 / 0.65 / 0.45 / 0.25` là tham số nội bộ, không hiển thị cho người dùng.
- Không fine-tune/LoRA.
- Không cần người dùng viết prompt hay chọn mức sáng tạo.

Không làm trong MVP v6.1: RAG, vector database, citation học thuật, Source-Grounded Rule Base, LLM Planner, Constraint Validator, taxonomy 8 nhãn, governance gate tiền kiểm, mobile, chatbot, payment và auth.

## 4. Pipeline hoạt động

### Giai đoạn 1 — Sinh hoa văn phẳng

1. Nhận ảnh hiện vật và mô tả nội bộ của nhóm.
2. Tách nền; suy màu viền từ mép ảnh.
3. Chạy Canny nhưng loại đường bao món đồ bằng mask co vào 14 px.
4. Nạp ControlNet cùng SD1.5 để sinh hoa văn, không nhắc “áo dài” trong prompt.
5. Dùng circular padding trên UNet và VAE, không áp lên ControlNet.
6. Sinh bốn biến thể theo weight nội bộ.
7. Biến thể 1 giữ bảng màu hiện vật gốc; các biến thể còn lại tạo đa dạng màu/bố cục theo hợp đồng code.

Prompt phải mô tả **flat decorative pattern**, phong cách men gốm, nét viền đậm, bố cục bất đối xứng và seamless repeating pattern. Negative prompt cố định phải chặn hình bình/lọ, ảnh chụp, người/m mannequin, đối xứng gương, màu neon, mờ, watermark và text.

### Giai đoạn 2 — Đưa hoa văn lên áo dài

1. Chọn ảnh áo dài mẫu làm nền dáng; SD không tự vẽ dáng người.
2. Hệ thống đánh giá bảy bố cục và chọn bố cục phù hợp nhất.
3. Ghép bằng mask mềm, displacement và shading.
4. Chạy một lượt img2img hoàn thiện với denoise `0.40`.
5. Xuất bốn ảnh áo dài hoàn chỉnh để người dùng chọn.

## 5. Dữ liệu và tiêu chí ảnh

MVP chốt `conditioning_mode = whole_object` để cả sáu ảnh được xử lý nhất quán. Không chọn ảnh chỉ dựa vào độ phân giải; tiêu chí đúng là số pixel cạnh hoa văn sau xử lý đạt ít nhất 60% ảnh mốc đã kiểm.

Giới hạn phải chấp nhận: ở weight cao, hoa văn có thể còn bóng dáng vật chứa vì dáng đó xuất hiện từ phân bố hoa văn trên mặt cong, không phải một đường viền đơn giản có thể lọc bỏ hoàn toàn.

## 6. UI/UX bắt buộc

Luồng người dùng:

1. Chọn hiện vật.
2. Bấm một nút Generate.
3. Chờ hệ thống sinh bộ bốn thiết kế.
4. Xem lưới bốn kết quả.
5. Chọn mẫu yêu thích.
6. Mở Design Passport.

Không được đưa slider Creative Intensity, ô prompt tự do hoặc bốn weight vào giao diện. Đây là hợp đồng “một nút”, không phải gợi ý tùy chọn.

## 7. Đánh giá và minh bạch

### Visual Similarity

Dùng similarity để so sánh tương đối giữa hoa văn nguồn và các biến thể. Không đặt threshold đạt/không đạt; metric chỉ hỗ trợ xếp hạng và phân tích đánh đổi.

### Design Passport

Passport cần cho người xem biết hiện vật đầu vào, mô tả nhóm, ảnh nguồn, phương án bố cục, weight nội bộ, seed, model, prompt template, negative prompt, thời gian chạy và file output được chọn.

### Audit Log

Audit Log phục vụ tái lập: mỗi lượt generate phải lưu input heritage, seed, model, weight, prompt, output path, similarity và thông tin lỗi nếu có.

## 8. Mã nguồn hiện có

- `generation/`: ControlNet, prompt, pattern, palette, garment compositing, layout và Stable Diffusion.
- `evaluation/`: sinh variants và intensity sweep.
- `data/heritage/`: sáu ảnh hiện vật dùng cho MVP.
- `data/garment/`: ảnh áo dài mẫu và layout.
- `outputs/`: smoke test và các biến thể đã sinh.
- `backend/`, `db/`, `rag/`: code legacy từ MVP cũ; không giao task mới và chưa xóa cho đến khi kiểm kê xong.

## 9. Tiêu chí nghiệm thu MVP

- Cả sáu hiện vật chạy được cùng pipeline.
- Mỗi hiện vật sinh đủ bốn output.
- Output là áo dài, không phải hình bình/lọ.
- Hoa văn được ghép lên áo dài, không chỉ xuất ảnh pattern rời.
- Seam của pattern không lộ đường nối bất thường.
- Weight là hằng số trong code, không đọc từ UI/config tùy ý.
- Có smoke test, seed và metadata để tái lập.
- Có Design Passport/Audit Log tối thiểu.
- Không có RAG/backend/governance cũ trong đường chạy active.

## 10. Rủi ro cần nói trung thực

- Weight cao giữ motif tốt hơn nhưng dễ giữ bóng dáng vật chứa.
- Weight thấp sinh dáng áo dài tốt hơn nhưng có thể xa hiện vật.
- Ảnh nguồn nhỏ vẫn có thể tốt nếu hoa văn chiếm phần lớn khung.
- License ảnh hiện có thể chưa xác minh; chỉ dùng nội bộ MVP nếu chưa có xác nhận bản quyền.
- GPU/VRAM, model download và thời gian inference là phụ thuộc môi trường local.

## 11. Kết luận định vị

MVP v6.1 không bán lời hứa “AI hiểu văn hóa và tự quyết định đúng/sai”. Nó trình diễn một pipeline kỹ thuật đo được: lấy hoa văn gốm, sinh nhiều phương án áo dài, cho người dùng chọn, rồi minh bạch quá trình sinh. Đây là phạm vi nhỏ hơn, chạy được hơn và phù hợp với output hiện đã kiểm thử.

Nguồn sự thật kỹ thuật: `docs/mvp_spec.md` (MVP Specification v6.1).
