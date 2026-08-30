# PHÂN CÔNG CÔNG VIỆC CHI TIẾT THEO VỊ TRÍ
## Tái sinh Di sản Số — Đội 3 người (DevOps/Software · AI/Data · BA)

---

## MỤC LỤC

1. Tổng quan phân vai
2. VỊ TRÍ 1 — AI/Data Engineer
3. VỊ TRÍ 2 — DevOps/Software Engineer
4. VỊ TRÍ 3 — Business Analyst (BA)
5. Ma trận phối hợp giữa 3 vị trí
6. Bàn giao (Handoff) quan trọng cần lưu ý

---

## 1. TỔNG QUAN PHÂN VAI

| Vị trí | Sở hữu chính | Không làm |
|---|---|---|
| **AI/Data** | RAG, LLM Planner, Stable Diffusion, ControlNet, CLIP Similarity, Constraint Engine (logic AI) | Không tự ý xác lập Rule Base nội dung (đó là việc của BA); không tự thiết kế UI |
| **DevOps/Software** | Hạ tầng, Database, Backend API, Streamlit Frontend, Audit Log, tích hợp end-to-end, ổn định demo | Không tự quyết định logic Governance (Validator rule phải theo đúng thiết kế đã thống nhất); không viết nội dung văn hóa |
| **BA** | Cultural Research, nội dung Rule Base, đặc tả chức năng, mockup, test case, hồ sơ dự án, dẫn dắt thuyết trình | Không code; không tự ý đổi kiến trúc kỹ thuật đã chốt |

---

## 2. VỊ TRÍ 1 — AI/DATA ENGINEER

### Trách nhiệm tổng thể
Làm chủ toàn bộ phần "trí tuệ" của hệ thống: từ truy xuất tri thức (RAG), diễn giải ý định (LLM Planner), đến sinh ảnh (Stable Diffusion/ControlNet) và đánh giá (CLIP Similarity).

### Công việc chi tiết theo ngày

**Ngày 1 — Review tính khả thi kỹ thuật**
- Tham gia buổi Project Freeze, đóng góp ý kiến kỹ thuật cho 8 nhãn enum (đảm bảo các nhãn có thể ánh xạ được sang điều khiển ControlNet thực tế).
- Deliverable: xác nhận bằng văn bản 8 nhãn enum là khả thi về mặt kỹ thuật.

**Ngày 2 — Setup môi trường AI**
- Setup Stable Diffusion + ControlNet trên Colab/Kaggle (chọn checkpoint phù hợp, kiểm tra GPU quota).
- Test chạy thử với 1 ảnh mẫu bất kỳ để xác nhận pipeline cơ bản hoạt động.
- Deliverable: môi trường AI sẵn sàng, notebook test chạy thành công.

**Ngày 3 — Hỗ trợ xử lý dữ liệu ảnh**
- Hỗ trợ chuẩn hóa format/kích thước ảnh heritage dataset (đảm bảo tương thích input cho SD/ControlNet).
- Review cùng BA để đảm bảo Rule Base content map đúng vào 8 nhãn enum về mặt kỹ thuật.
- Deliverable: bộ ảnh đã tiền xử lý sẵn sàng dùng cho generation.

**Ngày 4 — RAG Ingestion (Evidence retrieval)**
- Xây pipeline: document cleaning → chunking → embedding → lưu vào vector DB.
- Deliverable: vector DB chứa embedding của toàn bộ tài liệu văn hóa (3-10 tài liệu do BA cung cấp).

**Ngày 5 — RAG Retrieval + Go/No-Go**
- Test retrieval với 5-10 câu query mẫu, đánh giá độ chính xác kết quả trả về.
- Ra quyết định Go/No-Go: nếu Rule Base retrieval (tra cứu category) qua vector search chưa ổn định, đề xuất chuyển sang structured lookup — lưu ý: **quyết định này chỉ áp dụng cho Rule Base retrieval, không áp dụng cho Evidence retrieval** (Evidence bắt buộc chạy vector search thật).
- Deliverable: Evidence retrieval hoạt động ổn định, quyết định rõ ràng về Rule Base retrieval.

**Ngày 6 — Baseline Generation**
- Xây generation baseline: heritage image → generic prompt (không qua Governance) → Stable Diffusion → output.
- Log đầy đủ: seed, model, prompt, output path.
- Deliverable: script baseline chạy được, log có cấu trúc.

**Ngày 7 — ControlNet + LoRA Decision**
- Test ControlNet trên 3-5 mẫu, đánh giá chất lượng giữ cấu trúc.
- Nếu còn thời gian, thử nghiệm thêm LoRA fine-tune nhẹ, so sánh với ControlNet đơn thuần.
- Ra quyết định cuối ngày: dùng ControlNet đơn thuần hay có thêm LoRA (quyết định này **không ảnh hưởng Definition of Done** — ControlNet một mình đã đủ điều kiện).
- Deliverable: Generation stack được khóa (locked), sẵn sàng cho tuần 2.

**Ngày 8 — Rà soát Rule Base cùng BA**
- Kiểm tra tính nhất quán kỹ thuật của Rule Base: đảm bảo mọi entry trong `preserve`/`modifiable`/`restricted` map đúng vào 8 nhãn enum đã định nghĩa, không có category lạ hoặc lỗi chính tả trong JSON.
- Deliverable: Rule Base đã pass kiểm tra kỹ thuật, sẵn sàng dùng cho Planner/Validator.

**Ngày 9 — LLM Transformation Planner (công việc trọng tâm nhất)**
- Implement Planner với input: user intent + RAG Evidence + Rule Base categories của heritage_id tương ứng + Product + Creative Mode.
- Implement cơ chế segmentation: tách 1 câu intent thành nhiều transformation item riêng biệt nếu có nhiều ý.
- Implement ép output theo enum: dùng structured output/function calling của LLM API; nếu không khả dụng, validate thủ công sau response.
- Implement self-consistency check: gọi Planner 2 lần độc lập cho mỗi item, so sánh nhãn trả về.
- Chạy Planner Classification Accuracy Test với 12-15 câu do BA chuẩn bị (Ngày 5), phối hợp cùng BA đánh giá kết quả (không tự chấm một mình để đảm bảo khách quan).
- Deliverable: LLM Planner hoạt động đầy đủ, kết quả accuracy test được ghi nhận.

**Ngày 10 — Constraint Validator**
- Implement logic validate: xử lý độc lập từng transformation item (set comparison với Rule Base), không dùng số lượng item làm proxy cho mơ hồ.
- Implement rule inconsistent_classification (khi self-consistency check phát hiện Planner trả nhãn khác nhau giữa 2 lần).
- Chạy đủ 6 test case đối kháng (bao gồm test multi-transformation hợp lệ), phối hợp BA xác nhận từng case đúng logic văn hóa.
- Deliverable: Validator pass toàn bộ 6 test case.

**Ngày 11 — Constraint Engine**
- Map Creative Mode (Preserve/Reimagine) → ControlNet conditioning weight cụ thể cho từng category đã ALLOW.
- Deliverable: Constraint Engine sinh ra generation instructions đầy đủ (weight cụ thể theo từng category).

**Ngày 12 — End-to-end Integration (phối hợp chặt với DevOps)**
- Nối toàn bộ luồng AI: Heritage → RAG Evidence → Planner → Validator → Constraint Engine → ControlNet → Stable Diffusion.
- Đây là ngày ưu tiên cao nhất, không làm việc khác song song.
- Deliverable: pipeline AI chạy được từ đầu đến cuối với dữ liệu thật.

**Ngày 13 — Visual Similarity Assessment**
- Implement CLIP embedding + cosine similarity giữa ảnh gốc và ảnh sinh ra.
- Test hành vi metric: original vs original (phải gần 100%), original vs generated, original vs ảnh không liên quan (phải thấp) — để xác nhận metric hoạt động hợp lý.
- Deliverable: hàm tính similarity hoạt động đúng, đã qua sanity check.

**Ngày 14 — Buffer (fix bug pipeline AI)**
- Tập trung xử lý mọi lỗi phát sinh từ Ngày 9-13.
- Deliverable: pipeline AI ổn định, sẵn sàng cho Definition of Done.

**Ngày 15-17 — Hỗ trợ tích hợp UI**
- Đảm bảo model inference chạy ổn định khi gọi từ Streamlit UI (do DevOps xây).
- Hỗ trợ hiển thị đúng similarity score và dữ liệu Passport lấy từ AI layer.

**Ngày 18 — Evaluation**
- Chạy 3-5 case study: Baseline vs Proposed, đảm bảo điều kiện thí nghiệm đúng (cùng seed, cùng prompt template nền, ControlNet weight đã định nghĩa rõ cho từng nhánh — xem mục 16.3 tài liệu MVP).
- Deliverable: bảng kết quả experiment đầy đủ.

**Ngày 19 — Buffer**
- Fix bug còn sót, không thêm feature mới.

**Ngày 20 — AI Disclosure**
- Viết phần kê khai: model đã dùng (Stable Diffusion version, ControlNet, CLIP, LLM API), thư viện, cách sử dụng.
- Deliverable: tài liệu AI disclosure đầy đủ, chính xác.

**Ngày 21 — Chuẩn bị fallback demo**
- Chuẩn bị sẵn output đã generate trước (pre-generated) phòng trường hợp live demo gặp lỗi API/GPU.

### Kỹ năng/công cụ cần có
- Python, PyTorch/Diffusers library.
- Prompt engineering, structured output/function calling với LLM API.
- Vector embedding, vector database (pgvector hoặc tương đương).
- CLIP model, cosine similarity.

---

## 3. VỊ TRÍ 2 — DEVOPS/SOFTWARE ENGINEER

### Trách nhiệm tổng thể
Làm chủ hạ tầng, tích hợp hệ thống, và đảm bảo mọi thứ chạy ổn định — đặc biệt là thời điểm demo trước BGK.

### Công việc chi tiết theo ngày

**Ngày 1 — Setup ban đầu**
- Khởi tạo GitHub repository theo cấu trúc đã thống nhất (xem mục 19 tài liệu MVP).
- Setup môi trường dev cơ bản (Python venv/conda, requirements.txt khung).
- Deliverable: repo sẵn sàng, cấu trúc thư mục đầy đủ.

**Ngày 2 — Setup hạ tầng dữ liệu**
- Setup Supabase project (Database + Storage + pgvector extension).
- Dựng khung FastAPI backend rỗng (health check endpoint).
- Deliverable: Supabase hoạt động, backend khung chạy được.

**Ngày 3 — Schema Database**
- Thiết kế và tạo schema DB cho Heritage Dataset và Rule Base (theo đúng cấu trúc JSON đã thống nhất, có trường `rule_sources`).
- Viết script import dữ liệu từ file JSON/CSV vào DB.
- Deliverable: DB có đầy đủ bảng, script import chạy được với dữ liệu mẫu.

**Ngày 4 — Hỗ trợ RAG infrastructure**
- Hỗ trợ AI/Data setup pgvector, đảm bảo kết nối AI ↔ DB thông suốt (connection string, quyền truy cập).
- Deliverable: AI/Data có thể query vector DB không lỗi kết nối.

**Ngày 5 — API tra cứu (nếu cần fallback)**
- Nếu AI/Data quyết định Rule Base retrieval chuyển sang structured lookup, viết API endpoint tra cứu category theo heritage_id (query trực tiếp, không qua vector search).
- Deliverable: endpoint lookup sẵn sàng (dùng hoặc không tùy quyết định Go/No-Go).

**Ngày 6 — Logging System**
- Xây hệ thống logging có cấu trúc cho Baseline generation (lưu seed/model/prompt/output theo schema Audit Log đã định nghĩa).
- Deliverable: mọi lần generate baseline đều được log đầy đủ, truy vấn lại được.

**Ngày 7 — Batch Generation Pipeline**
- Chuẩn bị script cho phép AI/Data chạy generation hàng loạt (batch) để tiết kiệm thời gian test ở tuần 2, thay vì chạy từng ảnh một thủ công.
- Deliverable: script batch generation sẵn sàng.

**Ngày 8 — Database Rule Base (versioning)**
- Hoàn thiện DB schema cho Rule Base, đảm bảo có khả năng lưu snapshot (phục vụ Audit Log ghi lại rule_base_snapshot tại từng thời điểm).
- Deliverable: DB hỗ trợ versioning/snapshot cho Rule Base.

**Ngày 9 — API Integration cho LLM**
- Setup kết nối API (Gemini/GPT) cho LLM Planner, bao gồm xử lý authentication, rate limit.
- Implement retry/fallback logic khi LLM trả lỗi format JSON (retry 1 lần, fallback về `other_unclassified` nếu vẫn lỗi).
- Deliverable: API integration ổn định, có cơ chế retry/fallback hoạt động đúng.

**Ngày 10 — Bắt đầu UI Allow/Restrict/Block**
- Bắt đầu implement giao diện Streamlit hiển thị 3 trạng thái quyết định (theo nội dung BA đã đặc tả ở mục 8 tài liệu đặc tả chức năng).
- Deliverable: khung UI cơ bản cho 3 trạng thái, chưa cần hoàn thiện style.

**Ngày 11 — Tích hợp Constraint Engine → Generation**
- Nối output của Constraint Engine (do AI/Data cung cấp) vào input của Generation pipeline.
- Deliverable: luồng dữ liệu từ Constraint Engine đến Generation thông suốt.

**Ngày 12 — End-to-end Integration (phối hợp chặt với AI/Data)**
- Đảm bảo toàn bộ module nối đúng thứ tự, xử lý lỗi giữa các bước (nếu 1 bước lỗi, không làm sập toàn bộ request).
- Ưu tiên cao nhất trong ngày, không làm việc khác song song.
- Deliverable: pipeline chạy được từ request đầu vào đến output cuối cùng qua API.

**Ngày 13 — Cultural Passport UI + Audit Log**
- Implement giao diện Cultural Passport (theo đặc tả mục 9 tài liệu đặc tả chức năng).
- Implement Audit Log ghi đầy đủ theo schema đã định nghĩa (timestamp, heritage_id, input_channel, transformations, validator_decisions, controlnet_weight, similarity_score, seed...).
- Deliverable: Cultural Passport hiển thị đúng dữ liệu, Audit Log ghi nhận đầy đủ mọi lượt generate.

**Ngày 14 — Buffer (fix bug integration)**
- Xử lý lỗi phát sinh khi tích hợp, đảm bảo Definition of Done: người ngoài team có thể chọn 1 heritage, nhập intent (nằm ngoài bộ 12-15 câu đã test), chạy được toàn bộ pipeline không lỗi.
- Deliverable: hệ thống đạt Definition of Done.

**Ngày 15-16 — Xây Streamlit UI hoàn chỉnh (công việc trọng tâm)**
- Implement đầy đủ 5 màn hình theo đặc tả BA: Explore → Understand → Create → Generate → Verify.
- Đảm bảo luồng chuyển màn hình đúng, dữ liệu hiển thị chính xác theo mục 11 (Data Requirements) trong tài liệu đặc tả chức năng.
- Deliverable: UI hoàn chỉnh, chạy được end-to-end qua giao diện.

**Ngày 17 — Hoàn thiện Visual Similarity UI + Passport UI**
- Đảm bảo hiển thị đúng similarity score kèm chú thích bắt buộc.
- Deliverable: Màn hình Verify hoàn chỉnh.

**Ngày 18 — Lưu trữ Evaluation Output**
- Lưu toàn bộ output/screenshot/log của 3-5 case study có cấu trúc, dễ truy xuất cho BA tổng hợp báo cáo.
- Deliverable: bộ dữ liệu evaluation có tổ chức, sẵn sàng cho BA sử dụng.

**Ngày 19 — Buffer (freeze demo)**
- Không thêm feature. Đảm bảo môi trường chạy ổn định cho lúc quay video/demo (kiểm tra GPU quota, API quota còn đủ, không có dependency conflict).
- Deliverable: môi trường demo đã "đóng băng", test chạy thử ổn định nhiều lần liên tiếp.

**Ngày 20 — Chuẩn hóa GitHub**
- Đảm bảo README có hướng dẫn cài đặt/chạy rõ ràng, chạy thử lại từ đầu để xác nhận đúng như hướng dẫn.
- Deliverable: repository sạch, README chính xác, có thể tái tạo (reproducible).

**Ngày 21 — Đảm bảo hạ tầng lúc quay demo**
- Theo dõi hệ thống trong lúc quay video, xử lý ngay nếu có sự cố kỹ thuật.
- Deliverable: video demo quay thành công, không gặp lỗi hạ tầng.

### Kỹ năng/công cụ cần có
- Python, FastAPI.
- Supabase/PostgreSQL, pgvector.
- Streamlit.
- Git/GitHub, CI cơ bản.
- Kỹ năng debug tích hợp hệ thống nhiều thành phần.

---

## 4. VỊ TRÍ 3 — BUSINESS ANALYST (BA)

### Trách nhiệm tổng thể
Làm chủ "chất liệu và tính đúng đắn" của dự án: đảm bảo hệ thống giải quyết đúng vấn đề, nội dung văn hóa có căn cứ, trải nghiệm người dùng hợp lý, và câu chuyện thuyết trình thuyết phục.

### Công việc chi tiết theo ngày

**Ngày 1 — Đặc tả chức năng (song song với setup kỹ thuật)**
- Chủ trì buổi Project Freeze, ghi chép và hoàn thiện MVP Spec v1.0 dạng văn bản dễ hiểu.
- Bắt đầu viết đặc tả chức năng cho 5 màn hình + 3 trạng thái quyết định (dùng khung đã có trong tài liệu đặc tả mẫu).
- Deliverable: MVP Spec v1.0 hoàn chỉnh; bản nháp đặc tả chức năng 5 màn hình.

**Ngày 2 — Mockup + Review kỹ thuật**
- Hoàn thiện mockup low-fidelity cho 5 màn hình (dùng Excalidraw/Figma cơ bản/PowerPoint).
- Cuối ngày: tổ chức buổi review 30-45 phút với AI/Data + DevOps để kiểm tra tính khả thi kỹ thuật của đặc tả (theo checklist mục 13 tài liệu đặc tả chức năng).
- Deliverable: mockup hoàn chỉnh, đã review và điều chỉnh theo phản hồi kỹ thuật.

**Ngày 2 (song song) — Bắt đầu Cultural Research**
- Tìm nguồn tài liệu văn hóa về gốm Bát Tràng (bảo tàng, học thuật, nguồn chính thống).
- Chọn 10-15 heritage candidate cụ thể.
- Deliverable: danh sách nguồn tài liệu + 10-15 heritage candidate.

**Ngày 3 — Xây dựng nội dung Rule Base (công việc trọng tâm nhất)**
- Với từng heritage item, xác định: category nào thuộc `preserve`, `modifiable`, `restricted` — dựa trên căn cứ tài liệu cụ thể, không theo cảm tính.
- Ghi rõ `rule_sources` cho từng entry (truy ngược được về tài liệu nào).
- Lưu ý quan trọng: không áp rule chung cho mọi mẫu (ví dụ `symbolic_element` có thể là `preserve` ở mẫu này nhưng `modifiable` ở mẫu khác, tùy nội dung tài liệu).
- Deliverable: Rule Base hoàn chỉnh cho 10-15 mẫu, có source mapping đầy đủ.

**Ngày 4 — Tổng hợp Corpus tài liệu cho RAG**
- Chuẩn bị 3-10 tài liệu văn hóa (đã tìm từ Ngày 2), làm sạch text, chuyển sang định dạng phù hợp để AI/Data ingest vào RAG.
- Deliverable: corpus tài liệu sẵn sàng, đã làm sạch.

**Ngày 5 — Chuẩn bị bộ test Intent**
- Viết trước 12-15 câu intent mẫu bằng tiếng Việt tự nhiên, đa dạng cách diễn đạt (bao gồm cả câu multi-transformation như "đổi màu nền và thay bố cục", câu mơ hồ, câu rõ ràng).
- Gán nhãn kỳ vọng (expected label) cho từng câu.
- Deliverable: bộ 12-15 câu test có nhãn kỳ vọng, dùng cho Ngày 9.

**Ngày 6 — Review Output Baseline**
- Xem output Baseline do AI/Data tạo, đánh giá bằng con mắt "người hiểu văn hóa" xem có hợp lý không, ghi chú vấn đề nếu có.
- Deliverable: ghi chú đánh giá Baseline.

**Ngày 7 — Chuẩn bị outline hồ sơ**
- Bắt đầu phác thảo outline README/hồ sơ dự án (Problem, Solution, Architecture...) — chưa cần viết đầy đủ, chỉ cấu trúc khung.
- Deliverable: outline hồ sơ.

**Ngày 8 — Rà soát tính nhất quán Rule Base**
- Cùng AI/Data rà soát lại toàn bộ Rule Base của 10-15 mẫu, xác nhận không còn mâu thuẫn logic (ví dụ không để 1 category vừa preserve vừa modifiable cho cùng 1 mẫu).
- Deliverable: Rule Base đã pass rà soát nhất quán.

**Ngày 9 — Đánh giá Accuracy Test (khách quan)**
- Chạy bộ 12-15 câu test đã chuẩn bị qua LLM Planner (phối hợp AI/Data), tự mình so sánh kết quả với nhãn kỳ vọng — đóng vai trò đánh giá độc lập (không để AI/Data tự chấm một mình).
- Ghi nhận tỷ lệ đúng, chuẩn bị cách trình bày phù hợp trong hồ sơ (không tuyên bố quá mức).
- Deliverable: kết quả Accuracy Test đã được đánh giá khách quan.

**Ngày 10 — Xác nhận Test Case đối kháng**
- Cùng AI/Data chạy 6 test case đối kháng, xác nhận từng case có kết quả đúng theo logic văn hóa mong đợi (không chỉ đúng về mặt code).
- Deliverable: 6 test case đã xác nhận đúng cả về kỹ thuật và văn hóa.

**Ngày 11 — Kiểm tra định nghĩa cường độ Creative Mode**
- Đánh giá xem cách map Creative Mode (Preserve/Reimagine) → cường độ biến đổi có hợp lý về mặt trải nghiệm và văn hóa không.
- Deliverable: xác nhận hoặc đề xuất điều chỉnh cường độ.

**Ngày 12 — Test thử với vai trò người dùng thật**
- Đứng ngoài quá trình integration, thử dùng hệ thống như một người dùng thật (không biết trước kỹ thuật), phát hiện sớm lỗi UX/logic.
- Deliverable: danh sách vấn đề UX phát hiện được (nếu có).

**Ngày 13 — Viết nội dung hiển thị Cultural Passport**
- Soạn nội dung/cách diễn đạt cụ thể cho từng trường trong Cultural Passport (đã có khung ở tài liệu đặc tả, giờ hoàn thiện với nội dung thật của từng heritage item).
- Deliverable: nội dung Cultural Passport hoàn chỉnh cho 10-15 mẫu.

**Ngày 14 — Chuẩn bị Intent ngoài bộ test**
- Chuẩn bị trước danh sách intent nằm ngoài bộ 12-15 câu đã test, dùng để xác nhận Definition of Done (người ngoài team chạy thử).
- Deliverable: bộ intent bổ sung cho việc kiểm thử Definition of Done.

**Ngày 15-16 — Review UI**
- Review giao diện do DevOps xây: kiểm tra ngôn ngữ, luồng có dễ hiểu với người dùng phổ thông (học sinh/sinh viên) không.
- Deliverable: phản hồi điều chỉnh UI (nếu cần).

**Ngày 17 — Kiểm tra tính nhất quán ngôn ngữ hiển thị**
- Đảm bảo nội dung hiển thị không dùng nhầm thuật ngữ đã quyết định tránh (ví dụ không gọi "Verification" thay vì "Assessment").
- Deliverable: xác nhận UI dùng đúng ngôn ngữ đã thống nhất.

**Ngày 18 — Tổng hợp kết quả Evaluation**
- Tổng hợp bảng kết quả Baseline vs Proposed thành nội dung dễ hiểu, viết phần đánh giá định tính (mô tả sự khác biệt quan sát được).
- Deliverable: phần Evaluation trong hồ sơ đã hoàn chỉnh.

**Ngày 19 — Hoàn thiện Demo Script**
- Viết chi tiết lời thoại, timing cho video demo (dựa trên khung demo script đã có trong tài liệu MVP).
- Deliverable: demo script hoàn chỉnh, sẵn sàng để quay.

**Ngày 20 — Chủ trì viết Hồ sơ dự án (công việc lớn nhất)**
- Viết đầy đủ: Problem Statement, Solution, Methodology, Rule Base sources, Limitations.
- Phối hợp AI/Data để tích hợp phần AI Disclosure vào hồ sơ tổng.
- Deliverable: hồ sơ dự án hoàn chỉnh, sẵn sàng nộp.

**Ngày 21 — Dẫn dắt thuyết trình/demo**
- Đóng vai trò chính trình bày trước BGK (hoặc phối hợp với người phù hợp nhất trong đội) — vì BA hiểu rõ nhất câu chuyện vấn đề-giải pháp.
- Deliverable: video demo hoàn chỉnh.

### Kỹ năng/công cụ cần có
- Kỹ năng research và tổng hợp tài liệu.
- Viết tài liệu kỹ thuật/spec (không cần biết code).
- Công cụ mockup cơ bản (Excalidraw, Figma, hoặc PowerPoint).
- Kỹ năng thuyết trình.

---

## 5. MA TRẬN PHỐI HỢP GIỮA 3 VỊ TRÍ

| Hoạt động | AI/Data | DevOps | BA |
|---|---|---|---|
| Ngày 1-2: Setup song song | Chủ trì | Chủ trì | Chủ trì (đặc tả + mockup) |
| Ngày 3: Rule Base | Hỗ trợ kỹ thuật | Xây schema DB | **Chủ trì nội dung** |
| Ngày 8: Rà soát Rule Base | **Đồng chủ trì** | — | **Đồng chủ trì** |
| Ngày 9: Planner + Accuracy Test | **Chủ trì implement** | Hỗ trợ API | **Đồng đánh giá kết quả** |
| Ngày 10: Validator + Test case | **Chủ trì implement** | Hỗ trợ UI | **Đồng xác nhận logic** |
| Ngày 12: End-to-end Integration | **Đồng chủ trì** | **Đồng chủ trì** | Quan sát/test thử |
| Ngày 15-16: Streamlit UI | Hỗ trợ | **Chủ trì** | Review |
| Ngày 18: Evaluation | **Chủ trì chạy experiment** | Lưu trữ dữ liệu | **Chủ trì tổng hợp báo cáo** |
| Ngày 20: Hồ sơ | Viết AI Disclosure | Chuẩn hóa GitHub | **Chủ trì viết hồ sơ** |
| Ngày 21: Demo | Chuẩn bị fallback | Đảm bảo hạ tầng | **Chủ trì thuyết trình** |

---

## 6. BÀN GIAO (HANDOFF) QUAN TRỌNG CẦN LƯU Ý

1. **Ngày 2 → Ngày 3:** BA bàn giao đặc tả/mockup đã review kỹ thuật cho DevOps làm tài liệu tham chiếu (dùng ở Ngày 15-16), không cần bàn giao lại chi tiết lúc đó.

2. **Ngày 3 → Ngày 9:** BA bàn giao Rule Base (nội dung) cho AI/Data — đây là bàn giao quan trọng nhất, cần đảm bảo AI/Data hiểu đúng ý nghĩa từng category trước khi code Planner/Validator.

3. **Ngày 5 → Ngày 9:** BA bàn giao bộ 12-15 câu test intent cho AI/Data — cần bàn giao sớm (Ngày 5) dù dùng ở Ngày 9, để AI/Data có thời gian xem trước, phát hiện sớm nếu câu nào không phù hợp với thiết kế enum.

4. **Ngày 14 → Ngày 15:** DevOps bàn giao pipeline backend đã ổn định (qua buffer Ngày 14) cho việc xây UI — nếu Ngày 14 chưa đạt Definition of Done, cần ưu tiên tuyệt đối xử lý trước khi bắt đầu Ngày 15.

5. **Ngày 18 → Ngày 20:** DevOps bàn giao dữ liệu evaluation có cấu trúc cho BA tổng hợp thành nội dung hồ sơ — cần đảm bảo dữ liệu đủ rõ ràng (screenshot, số liệu) để BA không phải hỏi lại nhiều.

---

*Tài liệu này là bản phân công tham chiếu, có thể điều chỉnh nhẹ theo tiến độ thực tế — đặc biệt tại 2 buffer ngày 14 và 19, nơi phân công có thể linh hoạt theo phần nào cần ưu tiên xử lý nhất.*
