# Hướng dẫn thử nghiệm hệ thống Tái Sinh Di Sản Số

Dành cho ban tổ chức. Một trang. Mục nào chưa có số đo thật thì ghi `[CẦN NHÓM ĐIỀN]`, không ước lượng.

## 1. Truy cập

| Mục | Nội dung |
|---|---|
| Link thử nghiệm | `[CẦN NHÓM ĐIỀN: link production sau khi chuyển]`. Bản Preview đã kiểm ngày 21/11/2026: `https://tai-sinh-di-san-so-25905pxi8-quoczai22s-projects.vercel.app` |
| Mã truy cập | `[CẦN NHÓM ĐIỀN nếu có; nếu không có ghi "không cần"]` |
| Khung giờ sinh ảnh trực tiếp | `[CẦN NHÓM ĐIỀN]` |
| Đầu mối liên hệ | `[CẦN NHÓM ĐIỀN: tên, email, số điện thoại]` |
| Video trình diễn (phương án cuối) | `[CẦN NHÓM ĐIỀN: link]` |

**Cần chủ tài khoản Vercel xử lý trước khi gửi link:** bản Preview đang bật Vercel Authentication nên người ngoài không mở được. Phải tắt bảo vệ này (hoặc cấp quyền xem cho ban tổ chức) rồi mở thử bằng cửa sổ ẩn danh.

## 2. Ba bước thử

1. Mở link, bấm **Studio**, chọn một trong 6 hiện vật gốm.
2. Bấm **Tạo thiết kế**. Hệ thống hiện trạng thái "Đang tạo ảnh" hoặc vị trí chờ.
3. Khi xong, xem 4 thiết kế (4 mức sáng tạo) trên trang kết quả. Mỗi thiết kế có hồ sơ nguồn gốc (Design Passport) đi kèm, hiện đọc qua API và tệp dữ liệu, chưa hiện trên giao diện web.

Nút **Xem ý nghĩa hoa văn** ở Studio mở cuốn sổ mô tả hoa văn, nguồn ảnh và giấy phép CC BY 4.0.

## 3. Hệ thống hoạt động thế nào khi bạn bấm

- Ảnh được sinh bằng GPU trên Modal (Tesla T4). Mỗi lần chỉ một lượt chạy, tối đa 2 lượt chờ. Hàng chờ đầy thì báo thử lại sau.
- Mỗi địa chỉ mạng được tối đa 10 lượt mỗi giờ.
- Nếu GPU không sẵn sàng, trang tự dùng **kết quả đã sinh sẵn** và hiện nhãn "Kết quả đã sinh sẵn, không phải sinh trực tiếp". Trường hợp này không phải sinh ảnh mới.
- Ảnh xuất qua API (`GET /passports/{id}/export`) có nhãn "Thiết kế hỗ trợ bởi AI" ở mép ảnh và trong dữ liệu PNG (xem `docs/ai_disclosure.md`). Trên trang web, mọi ảnh do AI hỗ trợ tạo (hoa văn, áo dài) có nhãn "Hỗ trợ bởi AI" ở góc ảnh, và file tải về từ web được in nhãn này ở góc dưới trái.

## 4. Thời gian chờ đã đo

| Môi trường | Một bộ 4 thiết kế | Nguồn |
|---|---|---|
| Máy nhóm, RTX 4060 Laptop 8 GB (20/11/2026) | 112 đến 142 giây (5 lần đo); lượt có sinh lại hoa văn lâu hơn | `docs/finals/08_KPI.md`, K20 |
| Modal, Tesla T4 | `[CẦN NHÓM ĐIỀN: đo một lượt đủ 4 mức, ghi cả lần đầu sau khi nghỉ vì container khởi động lại]` | chưa đo |

## 5. Giới hạn đã biết

- Giao diện web chỉ còn 3 trang: chưa hiện Passport và chỉ số chất lượng.
- Có thiết kế được gắn nhãn "có cảnh báo" hoặc "không đạt" từ cổng chất lượng. Đây là hành vi đúng của hệ thống, không phải lỗi. Hiện vật LR3D_124 hay bị loại vì đường nối hoa văn.
- **Chưa có người am hiểu di sản hoặc thiết kế thẩm định mẫu**, và chưa có chấm mù của người thật (xem `docs/evidence/README.md`).
- Chưa thử ba người dùng thật cùng lúc và chưa thử khởi động lại container sau khi job xong (`docs/DEPLOY_LIVE.md`).
- Giấy phép ảnh nguồn là CC BY 4.0 của bộ dữ liệu LR3D-CULT2; nhóm chưa xác minh riêng nguồn của từng vật.

## 6. Tài liệu liên quan

- Minh chứng theo từng yêu cầu: `docs/evidence/README.md`
- Khai báo công cụ AI: `docs/ai_disclosure.md`
- Nguồn và giấy phép: `docs/DANH_MUC_NGUON_HIEN_VAT.md`
- Cách triển khai: `docs/DEPLOY_LIVE.md`
