# Bộ 48 Test Cases Kiểm Thử Cơ Chế Cảnh Báo & Chẩn Đoán Của Zalo Bot (Nhóm Vận Hành)

Bộ test case này bao quát toàn diện các tình huống sự cố thực tế theo 6 nhóm lỗi (mỗi nhóm 8 kịch bản, tổng cộng 48 test case), đối chiếu giữa **Mã lỗi kỹ thuật**, **Nguyên nhân cốt lõi**, **Phản hồi bằng ngôn ngữ tự nhiên (văn phong Việt Nam)** và **Gợi ý xử lý thực tế**.

---

## 1. Nhóm 1: Xác Thực & Khóa Truy Cập (Auth & API Keys) - 8 kịch bản

| ID | Tình huống kỹ thuật | Nguyên nhân cốt lõi | Cách Bot diễn giải bằng tiếng Việt tự nhiên | Hướng xử lý gợi ý |
|---|---|---|---|---|
| TC-01 | Modal trả HTTP 401 Unauthorized khi gọi `/generate` | `MODAL_KEY` trên Vercel không khớp `DH_API_KEY` trong Modal secret | *"Dạ máy chủ Modal báo từ chối truy cập do khóa kết nối không trùng khớp. Hệ thống đã tự chuyển sang ảnh mẫu để khách không thấy lỗi."* | Đối chiếu `MODAL_KEY` trên Vercel và Modal secret |
| TC-02 | Modal trả HTTP 403 Forbidden khi tải ảnh từ `/media/run` | Khóa API gửi lên không có quyền truy cập Volume outputs | *"Dạ đường dẫn lấy ảnh bị chặn quyền truy cập. Khách vẫn đang xem được ảnh đệm sẵn."* | Kiểm tra phân quyền truy cập Volume trên Modal |
| TC-03 | Biến `MODAL_KEY` bị xóa hoặc rỗng trên Vercel | Vercel Function thiếu biến môi trường cần thiết | *"Dạ hệ thống phát hiện Vercel chưa được nạp khóa kết nối tới GPU Modal."* | Kiểm tra cài đặt Environment Variables trên Vercel |
| TC-04 | Biến `MODAL_URL` bị đặt sai định dạng hoặc domain cũ | URL trỏ tới workspace hoặc tên app đã đổi | *"Dạ địa chỉ máy chủ GPU đang trỏ vào một đường link không tồn tại."* | Kiểm tra lại `MODAL_URL` xem đúng workspace Modal hiện tại không |
| TC-05 | Webhook Zalo gửi request nhưng header `x-bot-api-secret-token` sai | Token bí mật bảo vệ webhook bị sửa hoặc lộ | Bot âm thầm trả HTTP 403, từ chối thực thi để chống kẻ xấu spam | Kiểm tra lại `ALERT_ZALO_WEBHOOK_SECRET` |
| TC-06 | Người dùng lạ không thuộc danh sách cho phép nhắn tin yêu cầu sửa lỗi | Vi phạm chính sách `operator_only` | Bot bỏ qua lệnh đánh thức/sửa lỗi từ người không có thẩm quyền | Chỉ admin/operator trong allowlist mới đánh thức được GPU |
| TC-07 | Key AI Groq (`GROQ_API_KEY`) hết hạn hoặc bị thu hồi | Groq trả HTTP 401 khi bot tóm tắt tình trạng | Bot tự chuyển sang OpenRouter Gemini Flash làm phương án dự phòng | Nạp lại API Key của Groq |
| TC-08 | Key OpenRouter (`OPENROUTER_API_KEY`) hết số dư hoặc lỗi token | OpenRouter trả HTTP 401 | Bot tự rớt về mẫu tóm tắt kỹ thuật tiếng Việt dựng sẵn | Nạp thêm credit cho tài khoản OpenRouter |

---

## 2. Nhóm 2: Tài Nguyên GPU & Khởi Động Container (GPU Lifecycle) - 8 kịch bản

| ID | Tình huống kỹ thuật | Nguyên nhân cốt lõi | Cách Bot diễn giải bằng tiếng Việt tự nhiên | Hướng xử lý gợi ý |
|---|---|---|---|---|
| TC-09 | Container GPU đang ngủ sâu, khởi động quá thời gian chờ (Cold Start > 25s) | Modal GPU T4 mất 40–60s để kéo model và nạp VRAM | *"Máy chủ GPU T4 đang trong giấc ngủ sâu nên cần khoảng 1 phút để khởi động lại. Web vẫn hoạt động bình thường qua bộ nhớ đệm."* | Nhắn "đánh thức GPU" trước khi diễn thuyết |
| TC-10 | GPU hết bộ nhớ VRAM (CUDA Out Of Memory - OOM) | Xử lý ảnh kích thước quá lớn hoặc batch size vượt ngưỡng | *"Cụm xử lý đồ họa bị đầy bộ nhớ tạm thời khi đang dựng hoa văn phức tạp."* | Khởi động lại container GPU hoặc giảm kích thước ảnh |
| TC-11 | Driver NVIDIA hoặc CUDA runtime trên Modal gặp lỗi | Modal worker host bị lỗi phần cứng GPU | *"Máy chủ tính toán gặp trục trặc phần cứng đồ họa tạm thời."* | Khởi tạo lại app Modal (`modal deploy`) |
| TC-12 | Modal Workspace hết hạn mức tài khoản (Monthly GPU Spend Limit reached) | Tài khoản hết credit hoặc chạm trần chi phí | *"Dạ tài khoản máy chủ GPU đã chạm giới hạn chi phí trong tháng."* | Kiểm tra hạn mức chi phí trên dashboard Modal |
| TC-13 | Hàng đợi sinh ảnh bị đầy (HTTP 429 Too Many Requests) | Quá nhiều người bấm nút tạo ảnh cùng lúc | *"Đang có nhiều lượt yêu cầu sinh ảnh cùng lúc, hàng đợi GPU đang bận phục vụ lượt trước."* | Đợi 1–2 phút cho lượt trước hoàn tất |
| TC-14 | Xung đột phiên sinh ảnh trên cùng một hiện vật (HTTP 409 Conflict) | Hai người cùng bấm tạo cho 1 bình gốm trong tích tắc | *"Đang có một lượt tạo ảnh cho bình này đang chạy dở, hệ thống đang tiếp tục theo dõi lượt đó."* | Chờ lượt hiện tại xong rồi mới sinh lượt mới |
| TC-15 | Container bị buộc dừng do quá thời gian xử lý (Job Timeout > 300s) | Xử lý ControlNet 4 biến thể bị treo vòng lặp | *"Lượt sinh ảnh kéo dài quá thời gian quy định nên hệ thống đã chủ động ngắt an toàn."* | Kiểm tra log job trên Modal Dashboard |
| TC-16 | Modal thu hồi container do không có request mới (Idle scale down) | Cơ chế tiết kiệm chi phí chuẩn của Serverless GPU | *"Máy chủ GPU vừa tự động chuyển sang chế độ tiết kiệm năng lượng do không có người dùng."* | Bình thường, không cần can thiệp trừ khi cần test ngay |

---

## 3. Nhóm 3: Đường Truyền & Mạng Quốc Tế (Network & Gateways) - 8 kịch bản

| ID | Tình huống kỹ thuật | Nguyên nhân cốt lõi | Cách Bot diễn giải bằng tiếng Việt tự nhiên | Hướng xử lý gợi ý |
|---|---|---|---|---|
| TC-17 | Lỗi HTTP 504 Gateway Timeout giữa Vercel và Modal | Mạng quốc tế chập chờn, Vercel ngắt kết nối sau 15–25s | *"Kết nối mạng giữa máy chủ giao diện và cụm GPU tạm thời bị nghẽn."* | Chờ vài giây rồi thử kiểm tra lại |
| TC-18 | Lỗi HTTP 502 Bad Gateway từ nhà mạng đám mây | Máy chủ biên của Modal trả mã lỗi hạ tầng | *"Cổng kết nối đám mây của máy chủ tính toán đang bảo trì hoặc chập chờn."* | Kiểm tra trang trạng thái Modal Status |
| TC-19 | Đứt cáp quang biển gây rớt gói tin liên tục (Fetch Network Failure) | Mất tuyến kết nối Internet ra máy chủ nước ngoài | *"Đường truyền mạng ra máy chủ quốc tế đang bị gián đoạn gói tin."* | Hệ thống tự dùng bộ ảnh đệm sẵn tại chỗ |
| TC-20 | Vercel Function đạt ngưỡng Serverless Execution Timeout (60s) | Bản kế hoạch Vercel Hobby ngắt sớm | *"Thời gian chờ của trang web đã chạm trần tối đa của gói dịch vụ."* | Giữ cơ chế poll bất đồng bộ (async polling) |
| TC-21 | Zalo Bot API không gửi được tin nhắn (Zalo API HTTP 500) | Máy chủ Zalo Developer Platform bị lỗi nội bộ | Hệ thống ghi log cảnh báo và không làm sập tiến trình tạo ảnh | Chờ Zalo phục hồi hạ tầng |
| TC-22 | Tin nhắn gửi sang Zalo vượt quá 2000 ký tự | Zalo Bot giới hạn độ dài tin văn bản | Bot tự ngắt đoạn và tóm tắt ngắn gọn dưới 500 ký tự | Luôn duy trì prompt tóm tắt ngắn |
| TC-23 | Ảnh gửi qua Zalo `sendPhoto` bị lỗi 400 do sai định dạng | Đường dẫn ảnh không công khai hoặc không có đuôi png/jpg | *"Không thể gửi ảnh trực tiếp vào Zalo do định dạng tệp chưa tương thích."* | Kiểm tra lại URL ảnh công khai trên Vercel |
| TC-24 | DNS của Modal không phân giải được từ Vercel edge | Trục trặc phân giải tên miền quốc tế | *"Không tìm thấy địa chỉ máy chủ tính toán qua hệ thống tên miền."* | Thử ping lại domain Modal từ công cụ ngoài |

---

## 4. Nhóm 4: Dữ Liệu Hiện Vật & Tệp Mô Hình (Data & Assets) - 8 kịch bản

| ID | Tình huống kỹ thuật | Nguyên nhân cốt lõi | Cách Bot diễn giải bằng tiếng Việt tự nhiên | Hướng xử lý gợi ý |
|---|---|---|---|---|
| TC-25 | Không tìm thấy mã hiện vật yêu cầu (HTTP 404 Không tìm thấy bình) | Người dùng gửi mã bình không có trong danh mục 6 bình | *"Hiện vật bạn chọn hiện chưa có trong bộ sưu tập 6 bình gốm tiêu biểu."* | Chọn lại từ bình 1 đến bình 6 |
| TC-26 | Tệp ảnh hiện vật gốc trên web bị xóa hoặc hỏng đường dẫn | Thiếu tệp ảnh PNG bình gốm trong `web_ui/assets/images/heritage` | *"Ảnh mẫu của bình gốm này đang bị thiếu trên máy chủ lưu trữ."* | Kiểm tra và đồng bộ lại thư mục ảnh |
| TC-27 | Tệp tóm tắt di sản `heritage.json` bị lỗi cú pháp JSON | Cập nhật file bị thiếu dấu ngoặc hoặc dấu phẩy | *"Dữ liệu thông tin di sản đang bị lỗi định dạng khi nạp."* | Kiểm tra cú pháp JSON bằng linter |
| TC-28 | Tệp mô hình 3D (.glb) bị lỗi không tải được vào khung xoay 360 | Trình duyệt không tải được tệp mô hình 3D | Web tự động chuyển sang ảnh phẳng 2D sắc nét để người xem không thấy trang bị trắng | Kiểm tra đường dẫn tệp 3D của bình |
| TC-29 | Thiếu tệp `demo_variants.json` khi chạy chế độ an toàn | Mất file dữ liệu dự phòng | *"Chế độ bảo vệ an toàn đang thiếu tệp mẫu đối chiếu."* | Giữ nguyên tệp `demo_variants.json` trong source |
| TC-30 | Không đọc được thẻ bài Passport di sản của thiết kế mới | File JSON passport chưa kịp ghi xong trên Volume | *"Hồ sơ truy xuất nguồn gốc đang được máy chủ hoàn thiện bước lưu trữ."* | Chờ thêm 5–10s để tệp hoàn tất |
| TC-31 | Lỗi cấp quyền giấy phép bản quyền CC BY 4.0 | Metadata thiếu nguồn tác giả hoặc DOI | *"Thông tin bản quyền và nguồn gốc của bình gốm chưa được điền đầy đủ."* | Bổ sung DOI và đơn vị lưu giữ vào metadata |
| TC-32 | Trùng lặp mã Run ID khi lưu kết quả tạo ảnh | Hệ thống sinh 2 lượt cùng 1 giây | Hệ thống tự động thêm mã phụ để không ghi đè dữ liệu cũ | Đảm bảo Run ID có timestamp chi tiết đến mili-giây |

---

## 5. Nhóm 5: Pipeline AI Dệt Hoa Văn & LoRA (AI Model Pipeline) - 8 kịch bản

| ID | Tình huống kỹ thuật | Nguyên nhân cốt lõi | Cách Bot diễn giải bằng tiếng Việt tự nhiên | Hướng xử lý gợi ý |
|---|---|---|---|---|
| TC-33 | Thiếu tệp trọng số LoRA áo dài trên máy chủ GPU | File trọng số `.safetensors` chưa được nạp lên Volume | *"Mô hình AI chưa tìm thấy bộ kiến thức dáng áo dài Việt Nam."* | Kiểm tra Volume `tai-sinh-di-san-outputs` trên Modal |
| TC-34 | Tệp trích xuất Canny biên hoa văn bị đen hoàn toàn | Ngưỡng Canny quá cao hoặc bình gốm men nhạt không có viền rõ | *"Độ tương phản hoa văn của bình quá thấp, AI khó nhận diện rõ đường nét."* | Điều chỉnh lại ngưỡng trích xuất biên nét |
| TC-35 | Trọng số ControlNet đặt quá cao làm méo tà áo | Cấu hình tham số độ bám hoa văn vượt ngưỡng tối ưu | *"Hoa văn bám quá mạnh khiến phom dáng áo dài bị biến dạng."* | Đặt trọng số ControlNet về mức chuẩn 0.65–0.75 |
| TC-36 | Tỷ lệ khung hình ảnh sinh ra không đạt chuẩn 512x512 | Input đầu vào không chia hết cho 8 | *"Kích thước ảnh đưa vào không khớp tỷ lệ chuẩn của mô hình."* | Kiểm tra bước tiền xử lý ảnh cắt |
| TC-37 | Thiếu mô hình nền Stable Diffusion 1.5 trên cache GPU | Container mới chưa tải xong checkpoint SD1.5 | *"Máy chủ đang tải bổ sung mô hình tạo ảnh cơ sở."* | Nạp sẵn checkpoint vào image Modal |
| TC-38 | Bộ lọc an toàn phát hiện chi tiết nhạy cảm giả (False positive Safety Checker) | Thuật toán nhận diện nhầm chi tiết nếp gấp áo | *"Hệ thống an toàn AI tạm giữ một biến thể do nghi ngờ nội dung không phù hợp."* | Xem lại prompt âm tính (negative prompt) |
| TC-39 | Ảnh sinh ra bị nhòe nét do quá ít bước lặp (Sampling steps < 15) | Cấu hình chạy nhanh bị đặt tham số quá thấp | *"Độ sắc nét của hoa văn chưa đạt chuẩn chất lượng."* | Giữ nguyên 25–30 bước Euler A |
| TC-40 | Seed ngẫu nhiên bị lỗi trả về kết quả rỗng | Trình sinh số ngẫu nhiên gặp lỗi phần cứng | *"Hệ thống không thể tạo hạt giống ngẫu nhiên cho lượt sinh này."* | Tự động sử dụng seed mặc định 42 |

---

## 6. Nhóm 6: CI/CD & Triển Khai Phát Hành (Deploy & Delivery) - 8 kịch bản

| ID | Tình huống kỹ thuật | Nguyên nhân cốt lõi | Cách Bot diễn giải bằng tiếng Việt tự nhiên | Hướng xử lý gợi ý |
|---|---|---|---|---|
| TC-41 | GitHub Actions build web thất bại do lỗi cú pháp JS | Push code có lỗi syntax lên nhánh main | *"Quy trình kiểm tra mã nguồn tự động phát hiện lỗi trước khi xuất bản."* | Xem log GitHub Actions để sửa đúng dòng lỗi |
| TC-42 | AWS CodeBuild triển khai Modal backend thất bại | Lỗi lệnh cài thư viện Python trên AWS | *"Đợt cập nhật máy chủ GPU qua AWS chưa thành công."* | Xem link chi tiết CodeBuild mà bot gửi trong nhóm |
| TC-43 | AWS Parameter Store thiếu cặp token CD (`modal-cd`) | Token truy cập Modal của CI bị hết hạn | *"Hệ thống đóng gói tự động thiếu chìa khóa mở máy chủ đám mây."* | Nạp lại token vào Parameter Store ap-southeast-2 |
| TC-44 | Vercel tự động rollback do hàm Serverless lỗi cú pháp lúc khởi động | File api bị lỗi syntax khi deploy | *"Phiên bản trang web vừa đẩy lên gặp lỗi khi khởi động, đang giữ bản ổn định cũ."* | Kiểm tra cú pháp toàn bộ file trong `web_ui/api/` |
| TC-45 | Đụng độ phiên bản Git khi merge (Merge Conflict) | Xung đột giữa nhanh_Quoc và main | *"Mã nguồn đang bị xung đột nhánh, chưa thể xuất bản phiên bản mới."* | Xử lý triệt để conflict trước khi push |
| TC-46 | Cooldown cảnh báo của bot đang bật (chống spam tin nhắn) | Lỗi xảy ra liên tục trong vòng 30 phút | Bot chỉ báo 1 lần trong nhóm để tránh làm phiền, các lần sau ghi vào log | Điều chỉnh `ALERT_COOLDOWN_MIN` nếu cần kiểm thử dồn dập |
| TC-47 | Tràn hạn ngạch gọi API của Groq (Rate Limit Exceeded) | Nhắn hỏi bot quá nhiều câu hỏi trong 1 phút | *"Dạ em đang trả lời hơi nhiều tin cùng lúc nên cần nghỉ 30 giây ạ."* | Chờ 30 giây rồi hỏi tiếp |
| TC-48 | Máy chủ phục vụ demo rớt hoàn toàn về chế độ tĩnh (Offline Mode) | Mất cả Vercel lẫn Modal | Web tự phục vụ toàn bộ ảnh và dữ liệu từ ổ cứng cục bộ không cần Internet | Vẫn mở trang web trình diễn bình thường cho giám khảo xem |
