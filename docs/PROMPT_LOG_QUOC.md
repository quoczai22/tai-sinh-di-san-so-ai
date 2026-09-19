---
title: "Prompt log MVP — phần phát triển của Quốc"
owner_role: "Thành viên phụ trách phát triển và kiểm thử MVP"
scope: "Streamlit/PyTorch, Web UI, API, audit log và vận hành local"
source: "Lịch sử trao đổi trực tiếp giữa Quốc và Codex"
normalization: "Prompt được biên tập sang văn phong học thuật, giữ nguyên mục tiêu, phạm vi và trình tự; không phải trích dẫn nguyên văn."
excluded: "Prompt của nhóm trưởng, trao đổi nội bộ của Anti, cache và thử nghiệm chỉ tồn tại ở local"
updated: "2026-09-19"
---

# Prompt log MVP — phần phát triển của Quốc

## Nguyên tắc chuẩn hoá

Các prompt dưới đây được viết lại từ yêu cầu gốc của Quốc để phù hợp hồ sơ học thuật: dùng câu mệnh lệnh rõ chủ thể, mục tiêu và tiêu chí kiểm tra. Việc chuẩn hoá **không thêm công việc, quyết định hoặc kết quả không có trong lịch sử trao đổi**. Thứ tự các mục phản ánh diễn tiến thực tế; transcript hiện có không lưu timestamp từng tin nhắn nên không tự điền thời gian.

Các yêu cầu do Quốc chuyển đạt từ nhóm trưởng vẫn được ghi là yêu cầu triển khai của Quốc, không phải prompt log của nhóm trưởng.

## Phase 1 — Xây dựng MVP chứng minh pipeline sinh ảnh

| STT | Prompt chuẩn hoá từ yêu cầu của Quốc | Mục tiêu | Kết quả/tiêu chí hoàn thành |
|---:|---|---|---|
| 1 | Ưu tiên tích hợp mô hình vào Streamlit và xác minh pipeline hoạt động trước khi triển khai giao diện hoàn chỉnh. | Xác lập thứ tự thực hiện MVP. | MVP Streamlit/PyTorch tách khỏi lớp thiết kế. |
| 2 | Thiết kế MVP theo hướng xử lý ảnh hiện vật, không phụ thuộc mô tả văn bản đang thiếu. | Không để thiếu metadata chặn tiến độ. | Luồng đầu vào tập trung vào ảnh. |
| 3 | Chỉ sử dụng tên hiện vật đang có; tạm thời không yêu cầu mô tả. | Xác định dữ liệu tối thiểu. | Chọn hiện vật không bị chặn bởi description. |
| 4 | Tích hợp pipeline model vào ứng dụng Streamlit để có thể chạy inference. | Chuẩn bị runtime MVP. | Có module inference trong app. |
| 5 | Phân định rõ PyTorch là runtime model và Streamlit là lớp giao diện/điều khiển. | Thống nhất kiến trúc. | UI không thay thế runtime mô hình. |
| 6 | Quy định đầu ra demo phải là ảnh được sinh bởi pipeline. | Tránh dùng ảnh minh hoạ thay output thật. | Kết quả là generated image. |
| 7 | Triển khai theo vòng lặp: chạy, kiểm tra lỗi và hiệu chỉnh cho đến khi pipeline hoạt động. | Bảo đảm có kiểm chứng kỹ thuật. | Pipeline được chạy và kiểm tra. |
| 8 | Tạo cấu hình VS Code để khởi chạy ứng dụng bằng F5. | Chuẩn hoá thao tác chạy local. | Có launch configuration. |
| 9 | Tách ứng dụng và cấu hình thành các module có trách nhiệm riêng; không dồn logic vào một file lớn. | Bảo trì mã nguồn. | Cấu trúc Streamlit được phân mô-đun. |
| 10 | Chỉ tạo commit checkpoint sau khi Quốc kiểm thử và xác nhận MVP ổn định. | Kiểm soát chất lượng trước commit. | Quốc xác nhận test ổn trước commit. |

## Phase 2 — Đánh giá và đồng bộ phương án tích hợp thiết kế

| STT | Prompt chuẩn hoá từ yêu cầu của Quốc | Mục tiêu | Kết quả/tiêu chí hoàn thành |
|---:|---|---|---|
| 11 | Bắt đầu hợp nhất thiết kế đã có với luồng sinh ảnh theo phương án phù hợp. | Chuyển từ MVP thuần model sang trải nghiệm có UI. | Khởi động phase tích hợp. |
| 12 | Tái sử dụng toàn bộ thiết kế đã được xây dựng, không thay bằng giao diện tối giản khác. | Bảo toàn thiết kế đã chốt. | Web UI được giữ trong phương án tích hợp. |
| 13 | Thử đưa nguyên trạng thiết kế tĩnh vào Streamlit để đánh giá khả năng tái sử dụng. | Kiểm chứng phương án port trực tiếp. | Có thử nghiệm, đối chiếu `a56f849`. |
| 14 | Kiểm tra regression sau thay đổi của Anti khi ứng dụng không còn chạy được. | Phát hiện và khoanh vùng lỗi. | Regression được rà soát trước khi tiếp tục. |
| 15 | Khôi phục trạng thái giao diện Streamlit tương ứng `a56f849` nhưng giữ cấu trúc Web UI hiện hành. | Cân bằng UI hoạt động và cấu trúc mới. | Điều chỉnh có kiểm soát, không reset phá dữ liệu. |
| 16 | Tạo checkpoint trước khi tách nhánh hoặc thực hiện merge lớn. | Bảo toàn trạng thái đã kiểm tra. | Có checkpoint trước thay đổi lớn. |
| 17 | Loại bỏ phần Streamlit legacy, giữ `web_ui`, rồi mới đồng bộ main của nhóm trưởng. | Giảm xung đột khi đồng bộ codebase. | Đối chiếu `f63a1ac`. |

## Phase 3 — Chuyển sang dữ liệu thật và chạy GPU

| STT | Prompt chuẩn hoá từ yêu cầu của Quốc | Mục tiêu | Kết quả/tiêu chí hoàn thành |
|---:|---|---|---|
| 18 | Nhập `metadata.json` do nhóm trưởng cung cấp và sử dụng dữ liệu thật thay cho mockup. | Bảo đảm tính xác thực dữ liệu hiện vật. | Metadata được import vào luồng ứng dụng. |
| 19 | Xây dựng Streamlit/PyTorch tối giản nhằm chứng minh model chạy được trước khi đầu tư giao diện. | Giữ phạm vi MVP rõ ràng. | MVP GPU hoạt động trước UI phức tạp. |
| 20 | Khắc phục lỗi `render_app()` thiếu `heritage_items` và `heritage_map`. | Khôi phục khả năng khởi động app. | Tham số render được đồng bộ dữ liệu. |
| 21 | Dọn phần cũ ngoài `web_ui` để tránh xung đột với main và legacy runtime. | Giảm nợ kỹ thuật. | Ranh giới legacy/Web UI được làm rõ. |
| 22 | Chạy inference bằng RTX 4050 khi CUDA khả dụng. | Chứng minh pipeline dùng GPU thật. | PyTorch/diffusers sử dụng GPU. |
| 23 | Sinh bốn ảnh thiết kế cho mỗi lượt chạy. | Xác định số biến thể output. | Job trả bốn output. |
| 24 | Hiển thị bốn ảnh đã sinh trên view. | Kết nối output backend với UI. | Không dùng ảnh mock trong output. |
| 25 | Commit checkpoint sau khi đã kiểm thử bước GPU và bốn ảnh output. | Khóa mốc MVP đã kiểm tra. | Có checkpoint theo yêu cầu. |

## Phase 4 — Giữ nguyên Web UI và kết nối API live

| STT | Prompt chuẩn hoá từ yêu cầu của Quốc | Mục tiêu | Kết quả/tiêu chí hoàn thành |
|---:|---|---|---|
| 26 | Đánh giá bằng chứng kỹ thuật về việc tái sử dụng Web UI trong hệ thống chạy model. | Ra quyết định dựa trên khả thi thực tế. | Có đánh giá kiến trúc/luồng chạy. |
| 27 | Ưu tiên tái sử dụng trực tiếp giao diện Web UI tĩnh. | Giữ đúng visual đã phê duyệt. | Không dựng lại design bằng widget Streamlit. |
| 28 | Chọn phương án giữ nguyên Web UI với rủi ro triển khai thấp nhất. | Giảm lỗi tích hợp. | Chọn Web UI tĩnh kết nối API bridge. |
| 29 | Lập kế hoạch theo phase; Quốc quản lý phạm vi và Anti là dev chính cho task được giao. | Quản trị task rõ trách nhiệm. | Plan/handoff được tạo. |
| 30 | Chuẩn hoá tên biến và xác định thời điểm giao task cho Anti trước khi tiếp tục. | Duy trì tính nhất quán code. | Naming và handoff được kiểm soát. |
| 31 | Thực hiện lần lượt các task API bridge theo plan đã duyệt. | Tránh triển khai dồn một lần. | Skeleton bridge, API live, job generation và endpoint config; `751f5ab`, `3fe9d6e`, `80e79be`, `279add6`, `bdccb82`. |
| 32 | Giữ deployment Vercel cũ để nhóm xem bản demo ổn định trong giai đoạn phát triển. | Bảo vệ demo khỏi thay đổi chưa ổn định. | Bản demo không bị thay bởi bản thử. |
| 33 | Loại phase 7 vì không cần thiết cho MVP. | Kiểm soát scope. | MVP chỉ giữ phase thiết yếu. |

## Phase 5 — Hiệu chỉnh logic nội dung và metadata

| STT | Prompt chuẩn hoá từ yêu cầu của Quốc | Mục tiêu | Kết quả/tiêu chí hoàn thành |
|---:|---|---|---|
| 34 | Loại bỏ filter/category dựa trên `whole_object`; chỉ hiển thị thông tin hiện vật cần thiết. | Phù hợp với cấu trúc dữ liệu MVP. | View không còn filter không khả thi. |
| 35 | Thay placeholder ảnh khi loading bằng mô tả các bước xử lý. | Không gây hiểu nhầm khi output chưa tồn tại. | Loading thể hiện tiến trình/bước. |
| 36 | Gỡ mô tả nội bộ ở card bước 1–2 và các liên kết tới filter đã bỏ. | Không lộ thông tin nội bộ/chức năng không dùng. | Đối chiếu `0a750a7`, `cc459c8`. |
| 37 | Giao task sửa các lỗi logic này và rà soát lỗi tương tự còn tồn đọng. | Kiểm tra hệ thống sau sửa. | Có review logic tổng thể. |
| 38 | Gỡ hoàn toàn nhãn kỹ thuật `Conditioning mode: whole_object` khỏi HTML hiển thị. | Làm sạch UI demo. | Không còn text kỹ thuật trên view. |
| 39 | Lấy mô tả hiện vật trực tiếp từ file JSON đã được cung cấp. | Bảo toàn nguồn dữ liệu thật. | Description được data-bound từ JSON. |
| 40 | Xác nhận cơ chế import, không ghi đè dữ liệu JSON, và kiểm tra vị trí file nguồn. | Tránh sai lệch dữ liệu. | Đường dẫn/import được kiểm tra. |
| 41 | Rà soát và tinh gọn file trong phần ownership của Quốc mà không ảnh hưởng phần của người khác. | Bảo trì code theo trách nhiệm. | Refactor có giới hạn phạm vi. |

## Phase 6 — Hoàn thiện trải nghiệm Web UI bốn bước

| STT | Prompt chuẩn hoá từ yêu cầu của Quốc | Mục tiêu | Kết quả/tiêu chí hoàn thành |
|---:|---|---|---|
| 42 | Khoá điều hướng header/step cho tới khi người dùng hoàn tất đúng bốn bước. | Ngăn xem kết quả cũ hoặc bỏ qua workflow. | Navigation mở/khóa theo state. |
| 43 | Tối ưu nội dung và bố cục tiêu đề chủ đề thành hai dòng cân xứng. | Nâng chất lượng trình bày. | Hero title được hiệu chỉnh. |
| 44 | Đổi nhãn “Xem hộ chiếu thiết kế” thành “Xem thiết kế”. | Dùng thuật ngữ đúng chức năng. | Nút/modal đổi nhãn. |
| 45 | Loại bỏ nội dung “hộ chiếu” và thuộc tính/bảng màu khỏi modal output. | Bám phạm vi nội dung đã chốt. | Modal không hiển thị palette. |
| 46 | Bảo đảm nút lưu/mở thiết kế truy cập đúng ảnh generated hoặc tải ảnh về máy. | Tạo hành vi output có tác dụng thật. | Nút liên kết output sinh thực tế. |
| 47 | Gỡ thông báo/footer thử nghiệm không cần thiết khỏi bản demo. | Làm sạch giao diện trình bày. | Nội dung thừa được loại bỏ. |
| 48 | Điều chỉnh layering của nhãn nguồn dữ liệu để không bị hình phượng che, và lặp lại nếu chưa đạt. | Đảm bảo khả năng đọc nội dung. | Z-index/bố cục được tinh chỉnh đến khi đọc được. |

## Phase 7 — Audit, vận hành F5, log và seed

| STT | Prompt chuẩn hoá từ yêu cầu của Quốc | Mục tiêu | Kết quả/tiêu chí hoàn thành |
|---:|---|---|---|
| 49 | Đánh giá và triển khai audit log JSON cho toàn bộ bước 1–4. | Truy vết workflow mà không ảnh hưởng đáng kể inference. | Audit ghi các mốc thực hiện. |
| 50 | Cấu hình VS Code để dừng port cũ, chạy port mới và kích hoạt audit log. | Chuẩn hoá vận hành local. | F5/launch script và audit workflow; `426f81b`. |
| 51 | Bảo đảm F5 mở đúng `http://127.0.0.1:5500/#heritage-cards-section`. | Tránh mở sai URL/port. | `9ef9fbf`, `dcdac19`. |
| 52 | Xác minh Web UI nhận đúng ảnh do backend sinh ra. | Loại khả năng dùng mock URL/output cũ. | Luồng job/result được kiểm tra. |
| 53 | Sửa lỗi PowerShell reset port do escape regex, khiến lệnh thoát mã 1. | Khôi phục workflow F5. | `c1ada8e`, `dcdac19`. |
| 54 | Giảm log console/polling lặp lại, nhưng vẫn giữ tiến trình 100% để đo thời gian. | Tăng khả năng theo dõi chạy model. | `92f910d`. |
| 55 | Điều tra nguyên nhân ảnh trùng khi chạy hai lượt liên tiếp. | Phát hiện vấn đề tái lập output. | Xác định seed cố định là nguyên nhân. |
| 56 | Đối chiếu repository để xác định seed chuẩn của nhóm trưởng. | Tránh dùng seed test local làm ground truth. | Seed `42` được xác minh trên `origin/main`. |
| 57 | Thiết kế seed ngẫu nhiên theo từng job, dùng seed liên tiếp cho bốn biến thể, và ghi seed vào audit. | Khác nhau giữa lượt sinh nhưng vẫn truy vết được. | Quy tắc seed/audit được xác định. |
| 58 | Chỉ sử dụng seed được xác minh từ repository khi làm tài liệu nộp. | Tách bằng chứng repo khỏi test local. | Ground truth dùng `origin/main`. |

## Phase 8 — Vệ sinh repository và hồ sơ nộp

| STT | Prompt chuẩn hoá từ yêu cầu của Quốc | Mục tiêu | Kết quả/tiêu chí hoàn thành |
|---:|---|---|---|
| 59 | Rà soát GitHub để phát hiện report handoff, file môi trường hoặc artifact không nên theo dõi. | Làm sạch repository. | Đối chiếu `2bc1375`, `54900d8`. |
| 60 | Bổ sung ignore và loại bỏ artifact không cần thiết khỏi repository khi đã xác định chính xác. | Ngăn cache/audit/test quay lại repo. | `.gitignore` và tracked artifact được rà soát. |
| 61 | Xuất prompt log phục vụ hồ sơ nộp bài. | Tạo bằng chứng quy trình phát triển. | Tạo tài liệu prompt log. |
| 62 | Loại bỏ prompt log dựa trên thử nghiệm local; chỉ lưu prompt do Quốc giao cho phần dev. | Tách phạm vi Quốc với nhóm trưởng và local test. | Log không dùng local test làm bằng chứng. |
| 63 | Chuẩn hoá prompt log thành bản chi tiết, học thuật, thể hiện prompt–mục tiêu–kết quả từng bước. | Hoàn thiện hồ sơ có thể kiểm tra. | Phiên bản tài liệu hiện tại. |

## Metadata xét duyệt và commit

| Dòng | Thời gian | Agent thực hiện | Người duyệt | Commit liên quan | Ghi chú |
|---|---|---|---|---|---|
| #1–#10 | Không lưu trong transcript | Codex | Quốc xác nhận test ở #10; các dòng khác cần xác nhận review kết quả | `2ad675b` | MVP Streamlit/PyTorch. |
| #11–#17 | Không lưu trong transcript | Codex / Anti theo phân công | Quốc yêu cầu checkpoint ở #16; các dòng khác cần xác nhận review kết quả | `a56f849`, `f63a1ac` | Có thay đổi phương án tích hợp. |
| #18–#25 | Không lưu trong transcript | Codex | Quốc yêu cầu checkpoint ở #25; các dòng khác cần xác nhận review kết quả | Các checkpoint Streamlit liên quan | Data thật, GPU và 4 output. |
| #26–#33 | Không lưu trong transcript | Codex / Anti theo phân công | Quốc xác thực tiếp tục ở #31; các dòng khác cần xác nhận review kết quả | `751f5ab`, `3fe9d6e`, `80e79be`, `279add6`, `bdccb82` | Web UI/API live. |
| #34–#41 | Không lưu trong transcript | Anti thực hiện, Codex kiểm tra khi được giao | Cần xác nhận review kết quả bởi Quốc | `0a750a7`, `cc459c8` | Logic và metadata. |
| #42–#48 | Không lưu trong transcript | Codex / Anti theo task | Cần xác nhận review kết quả bởi Quốc | Chưa gắn commit duy nhất | UX bốn bước. |
| #49–#58 | Không lưu trong transcript | Codex | Cần xác nhận review kết quả bởi Quốc | `426f81b`, `9ef9fbf`, `c1ada8e`, `dcdac19`, `92f910d` | Audit/F5/log/seed. |
| #59–#63 | Không lưu trong transcript | Codex | Cần xác nhận review/đóng gói bởi Quốc | `2bc1375`, `54900d8` | Hygiene và hồ sơ. |

## Prompt bị bác bỏ, phát hiện lỗi hoặc phải làm lại

| Dòng gốc | Trạng thái | Bản sửa/cuối cùng |
|---:|---|---|
| #13 | Bị sửa lại — port trực tiếp design vào Streamlit không phải hướng cuối. | #26–#31: Web UI tĩnh kết nối API bridge. |
| #14 | Phát hiện regression sau thay đổi bên ngoài. | #15–#17: kiểm tra, checkpoint và đồng bộ lại. |
| #20 | Lỗi runtime thiếu tham số `render_app()`. | Đồng bộ lời gọi render với dữ liệu hiện vật. |
| #34 | Logic filter `whole_object` bị loại vì không phù hợp MVP. | Chỉ hiển thị thông tin hiện vật cần thiết. |
| #38 | Nhãn kỹ thuật lộ ra UI và bị gỡ. | Không hiển thị `Conditioning mode`. |
| #48 | Lần điều chỉnh đầu chưa hết che nhãn nguồn. | Tiếp tục chỉnh z-index/bố cục. |
| #53 | Port reset lỗi escape regex. | Sửa tại `c1ada8e`, `dcdac19`. |
| #55 | Output trùng do seed cố định. | #57–#58: quy tắc seed/audit và repo ground truth. |
| #62 | Prompt log local/test bị loại khỏi hồ sơ MVP. | Chỉ dùng log của Quốc, đối chiếu remote khi cần. |

## Đối chiếu và xác nhận trước khi nộp

- Ref đối chiếu: `origin/main` tại `54900d87ee153e75b1fd38b1af4c4e327d12e3e3`; 68 commit tại thời điểm rà soát.
- Ngày commit đầu tiên: **2026-08-28**, commit `dc2ac42`.
- Đã quét và che thông tin nhạy cảm: **Có, 0 chỗ cần che**. Không phát hiện chuỗi bí mật, thông tin liên hệ hoặc dữ liệu truy cập trong tài liệu.
- Số dòng có prompt bị bác bỏ/sửa lại: **9**.
- Số dòng thiếu người duyệt đã xác minh: **61/63**. Chỉ #10 (Quốc test ổn trước commit) và #31 (Quốc xác thực tiếp tục) có bằng chứng trực tiếp trong transcript; các dòng còn lại không được tự nhận là đã review.
- So với ngày hồ sơ khai bắt đầu: **chưa xác minh** vì chưa có ngày dự án chính thức. Không đóng gói bản cuối cho đến khi Quốc cung cấp ngày này; nếu muộn hơn 2026-08-28, cần kèm giải thích giai đoạn chuẩn bị sớm hơn.
- Thay đổi chưa commit ở local, cache model, ảnh test và audit test không được dùng làm bằng chứng trong prompt log.

