# TÁI SINH DI SẢN SỐ
## MVP Specification — Bản hoàn chỉnh (v3.0)

> **AI sáng tạo từ di sản, không sáng tạo lại lịch sử.**

---

## MỤC LỤC

1. Tổng quan dự án
2. Bối cảnh và vấn đề
3. Phạm vi MVP (cố định)
4. Đối tượng sử dụng
5. Kiến trúc tổng thể — 4 lớp
6. Taxonomy — Enum cố định
7. Heritage Dataset & Source-Grounded Rule Base
8. RAG — Knowledge Layer
9. LLM Transformation Planner
10. Constraint Validator
11. Constraint Engine & Creative Mode
12. Generative AI Layer
13. Visual Similarity Assessment
14. Cultural Passport & Audit Log
15. Trải nghiệm người dùng (UX)
16. Thiết kế thực nghiệm (Baseline vs Proposed)
17. Evaluation Framework
18. Tech Stack
19. Cấu trúc repository
20. Timeline 21 ngày
21. Phân công đội 3 người
22. Test case đối kháng
23. Rủi ro và cách xử lý
24. Những điều KHÔNG làm trong 3 tuần
25. Demo script
26. Core Innovation Statement & Pitch
27. Khả năng mở rộng

---

## 1. TỔNG QUAN DỰ ÁN

**Tái sinh Di sản Số** là nền tảng AI cho phép người trẻ khám phá và tái sáng tạo di sản văn hóa Việt Nam (mở đầu bằng họa tiết gốm Bát Tràng) thành nội dung sáng tạo hiện đại (thiết kế áo thun), trong khi vẫn đảm bảo tính minh bạch và trách nhiệm với nguồn gốc văn hóa.

**Một câu mô tả kỹ thuật:**

> Hệ thống sử dụng RAG để truy xuất bằng chứng văn hóa có nguồn, một Source-Grounded Cultural Rule Base để xác lập ràng buộc theo từng hiện vật di sản cụ thể, một LLM Planner (được cấp ngữ cảnh Rule Base và có cơ chế phát hiện ý định mơ hồ) để diễn giải yêu cầu người dùng thành nhãn cố định, một Validator tất định để ra quyết định ALLOW/RESTRICT/BLOCK, và Generative AI để tạo ra thiết kế mới — mọi quyết định đều được ghi lại minh bạch qua Cultural Passport và Audit Log.

**Điểm khác biệt cốt lõi:** dự án không cạnh tranh bằng "tạo ảnh đẹp hơn", mà bằng việc xây dựng một **Cultural AI Layer** — lớp trung gian có trách nhiệm nằm giữa sáng tạo của con người và Generative AI.

---

## 2. BỐI CẢNH VÀ VẤN ĐỀ

### 2.1. Bối cảnh chính sách

Nghị quyết 80-NQ/TW (07/01/2026) xác định văn hóa là nguồn lực nội sinh, đồng thời yêu cầu phát triển công nghiệp văn hóa và ứng dụng công nghệ số trong bảo tồn, phát huy di sản.

### 2.2. Ba vấn đề cụ thể

**Vấn đề 1 — Khoảng cách tiếp cận:** di sản tồn tại nhưng chưa được chuyển hóa thành trải nghiệm mà người trẻ có thể tương tác và sáng tạo cùng.

**Vấn đề 2 — Generative AI có thể làm mất ngữ cảnh văn hóa:** AI hiện nay có thể tạo ra hình ảnh "trông có vẻ truyền thống" nhưng không đảm bảo nguồn gốc motif, tính chính xác văn hóa, hay khả năng phân biệt phần nguyên bản với phần AI biến tấu.

**Vấn đề 3 — Thiếu cơ chế minh bạch nguồn gốc:** người xem sản phẩm AI-generated thường không biết phần nào là di sản gốc, phần nào là sáng tạo của AI, và sản phẩm dựa trên nguồn tư liệu nào.

**Vấn đề 4 (bổ sung, quan trọng về UX) — Rào cản kỹ năng prompt:** đối tượng người dùng mục tiêu (học sinh, sinh viên, content creator trẻ) phần lớn không có kinh nghiệm prompt engineering. Một hệ thống chỉ nhận input dạng văn bản tự do sẽ tạo rào cản sử dụng thực tế và tăng rủi ro hiểu sai ý định.

---

## 3. PHẠM VI MVP (CỐ ĐỊNH — KHÔNG THAY ĐỔI SAU NGÀY 1)

| Thành phần | Quyết định |
|---|---|
| Di sản | Gốm Bát Tràng |
| Số mẫu | 10–15 heritage items |
| Sản phẩm đầu ra | T-shirt design (duy nhất) |
| Generation | Stable Diffusion + ControlNet |
| Fine-tune | LoRA — **optional, không nằm trong Definition of Done** |
| Knowledge | RAG (Evidence retrieval) + Source-Grounded Rule Base (theo từng item) |
| LLM Planner | Enum-constrained, có Rule Base context, có phát hiện ambiguous intent |
| Governance | Validator tất định (default-deny: unknown → RESTRICT) |
| Creative mode | Preserve / Reimagine (kiểm soát cường độ, không phải nhị phân tuyệt đối) |
| Verification | Visual Similarity Assessment (không phải "xác thực văn hóa") |
| Transparency | Cultural Passport + Audit Log |
| Input UX | **Guided (checkbox) là chính, text tự do là mở rộng** |
| Baseline | Cùng prompt template, chỉ khác constraint block |
| Frontend | Streamlit |
| Human survey diện rộng | Không |
| Mobile / Chatbot / Payment / Multi-heritage / Multi-product | Không |

**Nguyên tắc khóa scope:**
> Nếu một tính năng không trực tiếp giúp chứng minh chuỗi `Heritage → RAG → Rule Base → Planner → Validator → Generate → Similarity → Passport`, thì không làm trong vòng loại.

---

## 4. ĐỐI TƯỢNG SỬ DỤNG

- **Nhóm 1 — Người trẻ:** học sinh, sinh viên muốn khám phá văn hóa và tạo nội dung sáng tạo.
- **Nhóm 2 — Content creator/designer:** cần chất liệu văn hóa Việt Nam có nguồn gốc xác thực cho sản phẩm sáng tạo.
- **Nhóm 3 — Đơn vị văn hóa:** bảo tàng, làng nghề muốn số hóa và tăng khả năng tiếp cận giới trẻ.

Cả ba nhóm đều **không giả định có kỹ năng prompt engineering** — đây là ràng buộc thiết kế xuyên suốt toàn bộ UX.

---

## 5. KIẾN TRÚC TỔNG THỂ — 4 LỚP

```text
┌─────────────────────────────────────────────────┐
│                1. KNOWLEDGE LAYER                │
│                                                   │
│  Heritage Dataset ──┬── RAG ────→ Evidence        │
│  (images+metadata)  │  (tài liệu văn hóa dài)     │
│                      └── Curation ─→ Source-      │
│                          Grounded Rule Base       │
│                          (theo từng heritage_id)  │
└───────────────────────────┬───────────────────────┘
                            ↓
┌─────────────────────────────────────────────────┐
│                2. GOVERNANCE LAYER                │
│                                                   │
│  User Input (checkbox HOẶC text tự do)            │
│         ↓ (nếu text tự do)                        │
│  Evidence + Rule Base categories + User Intent    │
│         ↓                                         │
│  LLM Transformation Planner                       │
│  (enum-constrained + ambiguous detection)         │
│         ↓                                         │
│  Constraint Validator (tất định, set comparison)  │
│         ↓                                         │
│  ALLOW / RESTRICT / BLOCK                         │
│         ↓                                         │
│  Constraint Engine (+ Creative Mode intensity)    │
└───────────────────────────┬───────────────────────┘
                            ↓
┌─────────────────────────────────────────────────┐
│                3. GENERATION LAYER                │
│    Stable Diffusion + ControlNet → T-shirt Design │
└───────────────────────────┬───────────────────────┘
                            ↓
┌─────────────────────────────────────────────────┐
│         4. TRANSPARENCY & ASSESSMENT LAYER        │
│  Visual Similarity Assessment + Cultural Passport │
│                  + Audit Log                       │
└─────────────────────────────────────────────────┘
```

**Lưu ý về đặt tên (đã sửa mâu thuẫn nội bộ):** lớp cuối cùng **không** được gọi là "Verification Layer" — vì mục 13 khẳng định rõ Visual Similarity Assessment không xác thực được tính đúng đắn văn hóa, dùng từ "Verification" ở cấp kiến trúc tổng sẽ mâu thuẫn trực tiếp với chính khẳng định đó. Tên gọi thống nhất xuyên suốt tài liệu: **Transparency & Assessment Layer**, gồm 3 thành phần: Visual Similarity Assessment (chỉ số tham khảo), Cultural Passport (minh bạch), Audit Log (truy vết).

**Ba vai trò không được gộp lẫn:**
- **RAG** → cung cấp evidence/context từ tài liệu văn hóa dài (retrieval thật, không lookup).
- **Rule Base** (do nhóm xây dựng, có căn cứ nguồn) → cung cấp constraint.
- **LLM Planner** → chỉ làm classification, không tự quyết định điều gì được phép.
- **Validator** → nơi duy nhất ra quyết định ALLOW/RESTRICT/BLOCK.

---

## 6. TAXONOMY — ENUM CỐ ĐỊNH

### 6.1. Tám nhãn transformation category (dùng chung toàn hệ thống)

```json
{
  "transformation_categories": [
    "background",
    "color_palette",
    "composition_layout",
    "core_motif",
    "symbolic_element",
    "product_context",
    "material_texture",
    "other_unclassified"
  ]
}
```

### 6.2. Bốn nhóm quyết định (ý nghĩa tách bạch, không chồng lấn)

| Nhóm | Ý nghĩa | Quyết định | Lý do hiển thị |
|---|---|---|---|
| `preserve` | Bắt buộc không được thay đổi | **BLOCK** | "Protected cultural element" |
| `modifiable` | Được phép thay đổi | **ALLOW** (cường độ theo Creative Mode) | — |
| `restricted` | Có thể thay đổi nhưng cần cảnh báo | **RESTRICT** | "Culturally sensitive attribute" |
| `other_unclassified` / ambiguous | Không map được rõ ràng, hoặc LLM phát hiện ý định mơ hồ | **RESTRICT** (fail-safe) | "Unclassified / ambiguous — fail-safe" |

**Quan trọng:** danh sách `preserve`/`modifiable`/`restricted` **không cố định chung cho mọi mẫu** — được xác lập **riêng theo từng heritage_id**, dựa trên tài liệu nguồn của chính mẫu đó (xem mục 7). Không có category nào (kể cả `symbolic_element`) bị mặc định cứng vào một nhóm cho toàn bộ dataset.

---

## 7. HERITAGE DATASET & SOURCE-GROUNDED CULTURAL RULE BASE

### 7.1. Heritage Dataset — schema mỗi mẫu

```json
{
  "heritage_id": "BT001",
  "name": "...",
  "origin": "Bát Tràng",
  "region": "Hà Nội",
  "cultural_meaning": "...",
  "image_path": "...",
  "source": ["SRC001", "SRC002"],
  "license": "..."
}
```

### 7.2. Rule Base — riêng theo từng heritage_id, có source mapping bắt buộc

```json
{
  "heritage_id": "BT001",
  "preserve": ["core_motif", "symbolic_element"],
  "modifiable": ["background", "color_palette", "composition_layout", "product_context", "material_texture"],
  "restricted": [],
  "rule_sources": {
    "core_motif": "SRC001",
    "symbolic_element": "SRC001"
  }
}
```

```json
{
  "heritage_id": "BT005",
  "preserve": ["core_motif"],
  "modifiable": ["background", "color_palette", "composition_layout", "product_context", "material_texture", "symbolic_element"],
  "restricted": [],
  "rule_sources": {
    "core_motif": "SRC003"
  }
}
```

**Lưu ý quan trọng:** ví dụ trên cho thấy `symbolic_element` ở BT001 thuộc `preserve` (vì tài liệu SRC001 chỉ ra ý nghĩa biểu tượng đặc biệt), nhưng ở BT005 lại thuộc `modifiable` (vì tài liệu tương ứng không ghi nhận ý nghĩa biểu tượng đặc thù). Đây là minh chứng cụ thể cho nguyên tắc: **không có category nào mặc định thuộc một nhóm cố định** — mọi rule đều truy ngược được về nguồn tài liệu cụ thể.

### 7.3. Tên gọi chính thức và định nghĩa

**Không gọi là "Verified Rule Base".**

**Tên chính thức: Source-Grounded Cultural Rule Base**

> Rule Base được xây dựng dựa trên các nguồn học thuật, tài liệu bảo tàng, hoặc tư liệu nghiên cứu có nguồn rõ ràng, được nhóm nghiên cứu và chuẩn hóa thành taxonomy theo từng heritage item trước khi đưa vào hệ thống. Đây **không phải** một chứng nhận chính thức về tính xác thực văn hóa từ cơ quan có thẩm quyền, mà là kết quả tổng hợp có căn cứ tài liệu của nhóm thực hiện dự án.

**Câu trả lời chuẩn khi bị hỏi "Ai verified?":** *"Rule Base không phải một chứng nhận chính thức, mà được nhóm tổng hợp có căn cứ từ [nguồn cụ thể] cho từng mẫu, với mọi rule đều truy ngược được về nguồn tài liệu tương ứng."*

---

## 8. RAG — KNOWLEDGE LAYER

### 8.1. Phân biệt hai loại truy xuất (quan trọng — không được gộp lẫn)

| Loại | Nguồn dữ liệu | Bắt buộc dùng vector search? |
|---|---|---|
| **Evidence retrieval** | Tài liệu văn hóa dài (PDF/học thuật), không có cấu trúc key-value | **Có** — đây là RAG thực chất, phải hoạt động (dù chỉ 3–10 tài liệu) |
| **Rule Base retrieval** | Category theo heritage_id, đã có cấu trúc JSON | Không bắt buộc — có thể dùng structured lookup nếu vector search chưa ổn |

**Nguyên tắc:** RAG là core selling point của dự án — không được fallback hoàn toàn sang lookup, nếu không "RAG" chỉ còn là từ trên slide. Go/No-Go tại cuối Ngày 5 chỉ áp dụng cho Rule Base retrieval.

### 8.2. Pipeline Evidence Retrieval

```text
Documents (3–10 tài liệu chất lượng)
       ↓
Cleaning → Chunking → Embedding → Vector Database
       ↓
User selects heritage
       ↓
Construct query
       ↓
Vector Search → Top-k chunks
       ↓
Evidence (có cấu trúc, có nguồn)
```

### 8.3. RAG phải trả Evidence có cấu trúc, không phải văn bản tự do

```json
{
  "context": "...",
  "sources": [
    {"document": "SRC001", "page": 12},
    {"document": "SRC002", "page": 8}
  ]
}
```

Điều này cho phép Cultural Passport hiển thị "Knowledge source: 2 references" thay vì mơ hồ "AI nói rằng...".

---

## 9. LLM TRANSFORMATION PLANNER

### 9.1. Vai trò chính xác

> **LLM Planner chỉ trả lời: "Người dùng muốn thay đổi cái gì?" — không trả lời "Cái gì được phép thay đổi?".**

Quyền quyết định "được phép" thuộc hoàn toàn về Validator (mục 10), dựa trên Rule Base.

### 9.2. Input (đã bổ sung Rule Base context — thay đổi quan trọng nhất)

```text
User intent (chỉ áp dụng cho kênh text tự do — xem mục 15)
+
RAG Evidence (cultural context của heritage item)
+
Rule Base categories của CHÍNH heritage_id này:
    preserve: [...]
    modifiable: [...]
    restricted: [...]
+
Product = T-shirt
+
Creative mode (Preserve / Reimagine)
```

Việc cấp Rule Base context giúp LLM phân loại có căn cứ, thay vì phân loại "mù" — giảm đáng kể rủi ro map sai nhãn (ví dụ nhầm "xóa hoa sen chính" thành `composition_layout` thay vì `core_motif`).

### 9.3. Output — tối giản, ép enum, tách bạch multi-transformation với ambiguity (đã sửa lỗi logic)

**Lỗi đã phát hiện và sửa:** thiết kế trước dùng "số lượng nhãn LLM trả về ≥ 2" làm proxy cho sự mơ hồ — đây là sai logic. Một câu như "đổi màu nền và thay bố cục" là **2 yêu cầu hợp lệ, rõ ràng, không mơ hồ**, nhưng thiết kế cũ sẽ tự động RESTRICT nhầm cả hai. Cần tách bạch hai khái niệm hoàn toàn khác nhau: **multi-transformation** (nhiều yêu cầu thay đổi hợp lệ trong một câu) và **ambiguity** (một cụm từ đơn lẻ không rõ nên map vào nhãn nào).

**Schema output mới — mỗi transformation là một item độc lập:**

```json
{
  "transformations": [
    {"raw_phrase": "đổi màu nền", "label": "color_palette"},
    {"raw_phrase": "thay bố cục", "label": "composition_layout"}
  ]
}
```

**Quy trình 2 bước:**
1. **Segmentation:** LLM tách câu intent thành các "yêu cầu thay đổi" riêng biệt trước (ví dụ 1 câu → 2 item nếu có 2 ý rõ ràng).
2. **Classification per item:** mỗi item được phân loại **độc lập** vào 1 trong 8 nhãn — số lượng item không còn liên quan đến việc có mơ hồ hay không.

**Cơ chế phát hiện ambiguity — dùng self-consistency check thay vì cờ tự khai báo:**

Vì để LLM tự gắn cờ `ambiguous: true/false` cho từng item cũng chỉ là một dạng tự khai báo không kiểm chứng được (giống vấn đề của `confidence` đã loại bỏ), MVP dùng cơ chế khách quan hơn:
- Với mỗi item, gọi LLM Planner **2 lần độc lập** (có thể temperature > 0 để tạo biến thiên tự nhiên).
- Nếu nhãn trả về **giống nhau** ở cả 2 lần → xử lý bình thường qua Validator theo nhãn đó.
- Nếu nhãn trả về **khác nhau** giữa 2 lần → đây là bằng chứng khách quan (đo được, không tự khai) rằng việc phân loại cụm từ này không ổn định → tự động RESTRICT với lý do `"inconsistent_classification"`.

**Lưu ý về nguyên tắc kiến trúc:** đây **không phải** thêm một tầng LLM Critic/Judge để kiểm tra LLM Planner (điều đã thống nhất không làm) — đây là gọi lại **cùng một Planner** để đo tính ổn định của chính nó, chi phí chỉ là 1 lệnh gọi LLM thêm cho mỗi item cần phân loại.

**Đã loại bỏ khỏi output (theo review):**
- ❌ `confidence: "high"` — LLM tự khai báo confidence không có giá trị khoa học nếu không có calibration riêng.
- ❌ `raw_user_intent` — backend tự lưu input gốc vào log, không cần LLM lặp lại.
- ❌ Cờ `ambiguous` tự khai báo trực tiếp — thay bằng self-consistency check (khách quan hơn).

### 9.4. Ép output theo enum — kỹ thuật cụ thể

1. Dùng **structured output / function calling** của LLM API (Gemini/GPT) với `enum` constraint trong schema — cách chắc chắn nhất.
2. Nếu không dùng được structured output: validate thủ công sau response, giá trị ngoài 8 nhãn → tự động gán `other_unclassified`.

### 9.5. Fallback khi LLM lỗi format

```text
LLM call → Parse JSON → Valid?
   No → Retry 1 lần với prompt nhắc rõ enum
   Vẫn lỗi → Fallback: "other_unclassified" (an toàn nhất)
```

### 9.6. Planner Classification Accuracy Test

- Chuẩn bị **12–15 câu intent mẫu** tiếng Việt tự nhiên, đa dạng cách diễn đạt, có gán nhãn kỳ vọng trước.
- Chạy Planner, so sánh với nhãn kỳ vọng, tính tỷ lệ đúng.
- **Cách trình bày đúng trong hồ sơ:** nêu như một quan sát sơ bộ trên tập mẫu nhỏ (ví dụ "10/15 câu phân loại đúng — cho thấy xu hướng phân loại hợp lý trên tập test hạn chế"), **không** dùng để khẳng định "Planner chính xác X%" như một chỉ số tổng quát đáng tin cậy.

### 9.7. Giới hạn cần thừa nhận rõ ràng (không được che giấu)

**Không tuyên bố:**
> ❌ "Hệ thống phát hiện mọi yêu cầu chưa biết."

**Diễn đạt đúng:**
> ✅ "Các yêu cầu không thể ánh xạ hợp lệ vào taxonomy đã định nghĩa, có lỗi định dạng, hoặc bị đánh giá là mơ hồ, sẽ được xử lý theo cơ chế fail-safe (mặc định RESTRICT). Enum đảm bảo LLM không tạo nhãn ngoài danh sách, nhưng không đảm bảo tuyệt đối LLM luôn chọn đúng nhãn về mặt ngữ nghĩa."

---

## 10. CONSTRAINT VALIDATOR

### 10.1. Logic — set comparison, tất định, xử lý ĐỘC LẬP từng transformation item (đã sửa bug logic)

**Bug đã sửa:** phiên bản trước coi `len(candidate_labels) >= 2` là dấu hiệu mơ hồ và RESTRICT toàn bộ — sai, vì nhiều yêu cầu hợp lệ trong một câu (multi-transformation) không đồng nghĩa với ambiguity. Validator giờ nhận vào danh sách **item đã qua self-consistency check** (mục 9.3) và xử lý **từng item một cách độc lập** — số lượng item không còn ảnh hưởng đến quyết định.

```python
def validate_item(label: str, consistency_status: str, rule_base: dict) -> dict:
    # consistency_status: "consistent" hoặc "inconsistent" (từ self-consistency check)
    if consistency_status == "inconsistent":
        return {"decision": "RESTRICT", "reason": "inconsistent_classification"}

    if label in rule_base["preserve"]:
        return {"decision": "BLOCK", "reason": "protected_cultural_element",
                "source": rule_base["rule_sources"].get(label)}
    elif label in rule_base["modifiable"]:
        return {"decision": "ALLOW", "item": label}
    elif label in rule_base["restricted"]:
        return {"decision": "RESTRICT", "reason": "culturally_sensitive_attribute"}
    else:  # other_unclassified hoặc không có trong Rule Base
        return {"decision": "RESTRICT", "reason": "unclassified_transformation_failsafe"}

def validate(transformations: list, rule_base: dict) -> list:
    # Mỗi transformation item được validate độc lập — không có "ambiguous vì nhiều item"
    return [validate_item(t["label"], t["consistency_status"], rule_base) for t in transformations]
```

**Ví dụ minh họa việc sửa lỗi:** với intent "đổi màu nền và thay bố cục" → 2 item (`color_palette`, `composition_layout`), cả hai đều nhất quán qua self-consistency check và đều thuộc `modifiable` → **cả hai ALLOW**, không còn bị RESTRICT oan như thiết kế cũ.

### 10.2. Về tính tất định — phạm vi áp dụng chính xác

> **Chỉ bước Validator là tất định 100%** (cùng input → cùng output, mọi lần). **Không tuyên bố toàn bộ hệ thống là deterministic** — vì LLM Planner (stochastic) và Stable Diffusion (stochastic, trừ khi fix seed) vẫn có thể cho kết quả khác nhau giữa các lần chạy.

Diễn đạt đúng: *"Constraint validation is deterministic; the overall generation pipeline is not, due to the stochastic nature of the LLM and diffusion model."*

---

## 11. CONSTRAINT ENGINE & CREATIVE MODE

### 11.1. ALLOW không đồng nghĩa "tự do tuyệt đối"

Đây là điểm bổ sung quan trọng: ALLOW chỉ xác định **phạm vi category** được phép biến đổi. **Cường độ** biến đổi trong phạm vi đó được điều tiết riêng bởi Creative Mode.

| | Category = preserve | Category = modifiable (ALLOW) |
|---|---|---|
| **Preserve mode** | BLOCK (luôn luôn) | ControlNet conditioning weight **cao** — biến đổi nhẹ |
| **Reimagine mode** | BLOCK (luôn luôn, không đổi theo mode) | ControlNet conditioning weight **thấp hơn** — biến đổi mạnh hơn |

**Nguyên tắc cố định:** category thuộc `preserve` luôn BLOCK bất kể Creative Mode nào — đây chính là ranh giới không đổi, không phụ thuộc vào mức độ sáng tạo người dùng chọn.

### 11.2. Constraint Engine output

```text
Validated categories (ALLOW list)
+
Creative Mode
       ↓
Generation instructions:
  - Preserve: [core_motif] → ControlNet weight = 0.9 (giữ cấu trúc chặt)
  - Modify (Preserve mode): [background, color_palette] → weight = 0.7
  - Modify (Reimagine mode): [background, color_palette] → weight = 0.3
```

---

## 12. GENERATIVE AI LAYER

### 12.1. Pipeline

```text
Original heritage image
       ↓
Preprocessing
       ↓
ControlNet (theo conditioning weight từ Constraint Engine)
       ↓
Stable Diffusion (theo prompt template — xem mục 16)
       ↓
Post-processing
       ↓
T-shirt Design Output
```

### 12.2. LoRA — trạng thái OPTIONAL, không nằm trong Definition of Done

```text
ControlNet works → MVP DONE.
```

LoRA chỉ thử nghiệm thêm ở Ngày 7 nếu dư thời gian, không xuất hiện trong bất kỳ tiêu chí "hoàn thành" nào của dự án.

---

## 13. VISUAL SIMILARITY ASSESSMENT

### 13.1. Tên gọi (không dùng "Verification" hay "Cultural Authenticity")

$$S_{visual} = \cos(E_{original}, E_{generated})$$

Trong đó $E$ là CLIP embedding.

### 13.2. Nguyên tắc sử dụng — không có threshold đạt/không đạt

> **Không quy định ngưỡng kiểu "score > 80% → đạt bảo tồn".** Chưa có cơ sở thực nghiệm để chọn một ngưỡng cụ thể; đặt threshold tùy tiện sẽ không đứng vững trước câu hỏi phản biện.

**Cách dùng đúng duy nhất:** so sánh **tương đối** giữa Baseline và Proposed trong cùng điều kiện thử nghiệm (mục 16). Trong Cultural Passport, hiển thị con số (ví dụ 87%) nhưng **không kèm diễn giải đạt/không đạt** — chỉ là chỉ số tham khảo.

Chú thích bắt buộc đi kèm mọi lần hiển thị:
> *Đo độ tương đồng thị giác (CLIP embedding) giữa di sản gốc và output. Đây không phải chứng nhận tính xác thực văn hóa (cultural authenticity), và không có ngưỡng "đạt/không đạt" được xác định.*

---

## 14. CULTURAL PASSPORT & AUDIT LOG

### 14.1. Cultural Passport

```text
╔════════════════════════════════════╗
║        CULTURAL PASSPORT            ║
╠════════════════════════════════════╣
║ HERITAGE                            ║
║ BT001 — [Tên họa tiết]              ║
║                                     ║
║ ORIGIN / CULTURAL MEANING           ║
║ ...                                 ║
║                                     ║
║ KNOWLEDGE SOURCES                   ║
║ ✓ SRC001 (trang 12)                 ║
║ ✓ SRC002 (trang 8)                  ║
║                                     ║
║ PRESERVED                           ║
║ ✓ Core motif (nguồn: SRC001)        ║
║                                     ║
║ MODIFIED                            ║
║ ✓ Background, Composition           ║
║                                     ║
║ RESTRICTED (nếu có)                 ║
║ ⚠ [category] — [lý do]              ║
║                                     ║
║ VISUAL SIMILARITY                   ║
║             87% (tham khảo)         ║
╚════════════════════════════════════╝
```

Nếu chế độ Reimagine với biến đổi mạnh:

```text
⚠ Strong transformation
Output này khác biệt đáng kể so với tham chiếu gốc.
Khuyến nghị xem xét tính phù hợp văn hóa trước khi
sử dụng thương mại.
```

### 14.2. Audit Log — ghi lại toàn bộ chuỗi quyết định

```text
timestamp
heritage_id
input_channel          # "checkbox" hoặc "free_text"
raw_user_intent         # nếu qua free_text
llm_transformations     # danh sách item [{raw_phrase, label, consistency_status}], nếu qua free_text
rule_base_snapshot      # preserve/modifiable/restricted tại thời điểm đó
validator_decisions     # danh sách quyết định, MỘT PHẦN TỬ CHO MỖI transformation item
reason
creative_mode
controlnet_weight       # giá trị weight thực tế dùng cho lần generate này (Baseline: cố định; Proposed: theo category)
similarity_score
seed
```

Phục vụ cả demo (chứng minh tính minh bạch) lẫn hồ sơ kê khai minh chứng theo yêu cầu BTC (lịch sử câu lệnh).

---

## 15. TRẢI NGHIỆM NGƯỜI DÙNG (UX)

### 15.1. Nguyên tắc thiết kế cốt lõi

> **Guided interaction (chọn lựa có cấu trúc) là kênh chính. Text tự do là kênh mở rộng.**

Lý do: đối tượng người dùng mục tiêu không có kinh nghiệm prompt engineering. Ép người dùng tự diễn đạt ý định bằng văn bản tự do làm tăng rào cản sử dụng và tăng rủi ro Planner phân loại sai.

### 15.2. Luồng 5 bước

```text
Bước 1 — Explore: chọn một di sản.
Bước 2 — Understand: xem ảnh gốc, nguồn gốc, ý nghĩa, đặc trưng (từ RAG Evidence).
Bước 3 — Create: chọn cách biến đổi (xem 15.3) + chọn Creative Mode.
Bước 4 — Generate: AI tạo output.
Bước 5 — Verify: xem Visual Similarity + Cultural Passport.
```

### 15.3. Screen 3 — Create (thiết kế chi tiết)

```text
┌─────────────────────────────────────────┐
│  Bạn muốn thay đổi gì ở thiết kế này?    │
│                                           │
│  [ ] Đổi màu nền                         │
│  [ ] Đổi tông màu chủ đạo                │
│  [ ] Thay đổi bố cục/cách sắp xếp        │
│  [ ] Ứng dụng vào ngữ cảnh khác           │
│  [ ] Thay đổi chất liệu bề mặt           │
│                                           │
│  ─────────── hoặc ───────────            │
│                                           │
│  Mô tả bằng lời của bạn (tùy chọn):       │
│  [___________________________]           │
│  ⓘ Hệ thống sẽ cố gắng hiểu, nhưng có   │
│     thể yêu cầu xác nhận lại nếu không   │
│     rõ ràng, hoặc từ chối nếu ảnh hưởng  │
│     đến yếu tố cần bảo tồn.               │
│                                           │
│  Creative Mode:  ○ Preserve  ○ Reimagine │
└─────────────────────────────────────────┘
```

### 15.4. Xử lý theo kênh input

| Kênh | Cách xử lý | Cần LLM Planner? |
|---|---|---|
| Chọn checkbox | Map trực tiếp 1-1 sang enum, bỏ qua bước phân loại ngôn ngữ tự nhiên | Không |
| Mô tả tự do | Qua LLM Planner (Rule Base context + ambiguous detection) → Validator | Có |

Phần lớn tương tác thực tế đi qua checkbox (nhanh, không rủi ro); kênh text tự do dành cho yêu cầu ngoài danh sách có sẵn — đây cũng chính là kênh dùng để trình diễn Governance Layer trong demo.

### 15.5. Màn hình phản hồi ALLOW/RESTRICT/BLOCK

```text
┌─────────────────────────────────────────┐
│  ✕ BLOCKED                               │
├─────────────────────────────────────────┤
│ Yêu cầu: "xóa hoa sen chính"             │
│ Phân loại: core_motif                    │
│                                           │
│ Lý do: Đây là yếu tố được xác định cần   │
│ bảo tồn, dựa trên nguồn [SRC001].         │
│                                           │
│ Hệ thống không thực hiện biến đổi này.   │
└─────────────────────────────────────────┘
```

---

## 16. THIẾT KẾ THỰC NGHIỆM (BASELINE vs PROPOSED)

### 16.1. Vấn đề cần tránh — confound trong thiết kế

Nếu Baseline và Proposed dùng hai prompt được viết độc lập, biến số thay đổi giữa hai điều kiện không chỉ là "có/không có Governance" mà còn lẫn "chất lượng prompt engineering" — đây là confound làm mất giá trị khoa học của toàn bộ so sánh.

### 16.2. Thiết kế đúng — dùng chung một template

```text
TEMPLATE CHUNG:
"A modern t-shirt design inspired by [heritage_name],
featuring [BASE_DESCRIPTION from RAG evidence].
{CONSTRAINT_BLOCK}
Style: contemporary, Gen Z appeal."

BASELINE:
  CONSTRAINT_BLOCK = "" (để trống)

PROPOSED:
  CONSTRAINT_BLOCK =
    "Preserve exactly: [preserve categories từ Rule Base].
     Free to modify: [modifiable categories, theo cường độ Creative Mode]."
```

**Điều kiện kiểm soát bắt buộc giống nhau giữa hai nhánh:** cùng heritage reference image, cùng base description, cùng model Stable Diffusion + ControlNet, cùng seed. **Biến số duy nhất thay đổi: có/không có constraint block trong prompt.**

Đây là cách trả lời trực tiếp câu hỏi phản biện: *"Kết quả tốt hơn vì Governance hay vì prompt viết khéo hơn?"* → *"Vì cùng một prompt nền, chỉ thêm/bớt đúng một khối constraint."*

### 16.3. Confound thứ hai đã phát hiện và sửa: ControlNet conditioning weight

**Vấn đề:** ngoài prompt template, Proposed còn dùng conditioning weight **thay đổi động theo category** (0.9 cho preserve, 0.7/0.3 cho modifiable tùy Creative Mode — mục 11.2). Nếu Baseline dùng một weight không được định nghĩa rõ (ví dụ mặc định của thư viện), đây là một biến số thứ hai không kiểm soát, độc lập với biến số constraint block — làm suy yếu giá trị so sánh.

**Điểm cần làm rõ:** đây **không phải** một confound cần loại bỏ hoàn toàn, vì differential weighting theo category chính là **cơ chế cốt lõi** mà Governance Layer mang lại — không phải hiệu ứng phụ tình cờ. Vấn đề thực sự là Baseline chưa được định nghĩa dùng weight nào một cách tường minh.

**Cách sửa — định nghĩa rõ ràng cả hai điều kiện:**

```text
BASELINE:
  ControlNet conditioning weight = MỘT GIÁ TRỊ CỐ ĐỊNH DUY NHẤT
  (ví dụ 0.5) áp dụng đồng đều cho toàn bộ ảnh, không phân biệt
  vùng/category nào.
  → đại diện cho "generation không có phân biệt văn hóa".

PROPOSED:
  ControlNet conditioning weight THAY ĐỔI theo category, do
  Constraint Engine xác định dựa trên Rule Base (mục 11.2).
  → đại diện cho "generation có governance-informed differentiation".
```

**Câu trả lời chuẩn khi bị hỏi "tại sao weight của Proposed khác Baseline?":**
> *"Đây chính là biến số đang được kiểm định. Baseline đại diện cho generation không phân biệt văn hóa (weight đồng nhất 0.5 toàn ảnh); Proposed đại diện cho generation có governance-informed differentiation (weight thích ứng theo category, xác lập từ Rule Base có nguồn gốc). Cả hai vẫn dùng chung một prompt template nền, chung model, chung seed."*

---

## 17. EVALUATION FRAMEWORK

### 17.1. AI Evaluation
- Visual Similarity Assessment (so sánh tương đối Baseline vs Proposed).
- Bảng experiment trên 3–5 heritage items × 2 modes:

| ID | Heritage | Method | Mode | Similarity |
|---|---|---|---|---:|
| 01 | BT001 | Baseline | Preserve | 0.xx |
| 02 | BT001 | Proposed | Preserve | 0.xx |
| 03 | BT001 | Baseline | Reimagine | 0.xx |
| 04 | BT001 | Proposed | Reimagine | 0.xx |

### 17.2. Qualitative comparison
So sánh trực quan (screenshot cạnh nhau): Original / Baseline / Proposed — thường thuyết phục hơn bảng số khi trình bày.

### 17.3. Planner Classification Accuracy
12–15 câu test, trình bày như quan sát sơ bộ (mục 9.6), không phải benchmark chính thức.

### 17.4. Những gì KHÔNG làm ở MVP
- Human evaluation khảo sát người dùng diện rộng (không đủ mẫu để có ý nghĩa thống kê).
- System evaluation chi tiết (chi phí inference, dashboard riêng) — chỉ nêu bằng lời nếu được hỏi.

---

## 18. TECH STACK

| Thành phần | Công nghệ |
|---|---|
| AI Generation | Stable Diffusion |
| Conditioning | ControlNet (LoRA optional) |
| Vision similarity | CLIP embedding |
| Knowledge Base | Supabase/PostgreSQL (+ pgvector) |
| RAG retrieval | Vector search (Evidence) + structured lookup (Rule Base nếu cần) |
| LLM | Gemini/GPT API — structured output/function calling |
| Backend | Python + FastAPI |
| Frontend | Streamlit |
| Storage | Supabase Storage |
| Experiment | Google Colab / Kaggle |
| Version control | GitHub |

---

## 19. CẤU TRÚC REPOSITORY

```text
digital-heritage-ai/
├── data/
│   ├── heritage/
│   ├── documents/
│   ├── metadata.json
│   └── rule_base.json          # theo từng heritage_id, có rule_sources
├── rag/
│   ├── ingest.py
│   ├── chunk.py
│   ├── embed.py
│   └── retrieve.py             # Evidence retrieval
├── governance/
│   ├── planner.py              # LLM Planner (enum + ambiguous detection)
│   ├── validator.py            # set comparison, tất định
│   └── constraint_engine.py    # + Creative Mode intensity
├── generation/
│   ├── controlnet.py
│   ├── stable_diffusion.py
│   └── prompt_template.py      # template dùng chung Baseline/Proposed
├── verification/
│   └── similarity.py
├── passport/
│   └── passport.py
├── evaluation/
│   ├── baseline.py
│   ├── planner_accuracy_test.py
│   ├── experiments.csv
│   └── evaluate.py
├── app/
│   └── streamlit_app.py        # UI checkbox + text tự do
├── outputs/
├── docs/
│   ├── dataset.md
│   ├── rule_base_sources.md
│   ├── ai_disclosure.md
│   └── methodology.md
├── audit_log.csv
└── README.md
```

---

## 20. TIMELINE 21 NGÀY

### 🟩 TUẦN 1 — KNOWLEDGE + GENERATION

| Ngày | Nội dung | Deliverable |
|---|---|---|
| 1 | Project Freeze: chốt scope, 8 nhãn enum, taxonomy 4 nhóm | MVP Spec v1.0 |
| 2 | Cultural Research: tìm nguồn, bắt đầu gán Rule Base theo từng mẫu + source mapping | Source registry |
| 3 | Heritage Dataset + Rule Base: hoàn thành 10–15 mẫu, không hardcode category nào | Dataset hoàn chỉnh |
| 4 | RAG Ingestion (Evidence): chunking, embedding, vector DB | Vector DB sẵn sàng |
| 5 | RAG Retrieval + Go/No-Go (chỉ cho Rule Base retrieval) | Evidence retrieval hoạt động |
| 6 | Baseline Generation: heritage → generic prompt → SD → output, log seed | Baseline pipeline |
| 7 | ControlNet + LoRA decision (LoRA không ảnh hưởng Definition of Done) | Generation stack khóa |

### 🟨 TUẦN 2 — GOVERNANCE + FULL PIPELINE

| Ngày | Nội dung | Deliverable |
|---|---|---|
| 8 | Hoàn thiện Rule Base (rà soát nhất quán, source mapping đầy đủ) | Rule Base hoàn chỉnh |
| 9 | LLM Planner (enum + Rule Base context + segmentation multi-transformation + self-consistency check 2 lần/item) + chuẩn bị 12–15 câu test | Planner hoạt động, không còn nhầm multi-transformation với ambiguity |
| 10 | Constraint Validator (xử lý độc lập từng transformation item) + bắt đầu UI Allow/Restrict/Block; chạy 6 test case đối kháng (bao gồm test multi-transformation hợp lệ) | Validator + test pass |
| 11 | Constraint Engine (map Creative Mode → conditioning weight) | Engine hoạt động |
| 12 | End-to-end Integration (milestone quan trọng nhất) | Pipeline đầy đủ |
| 13 | Visual Similarity + Cultural Passport + Audit Log | Verification layer |
| 14 | **BUFFER** — Definition of Done: người ngoài team chạy pipeline với intent ngoài bộ 12–15 câu đã test | MVP backend hoàn chỉnh |

### 🟦 TUẦN 3 — PRODUCT + EVALUATION + DEMO

| Ngày | Nội dung | Deliverable |
|---|---|---|
| 15–16 | Streamlit UI: Explore→Understand→Create (checkbox+text)→Generate | UI hoàn chỉnh |
| 17 | Visual Similarity UI + Cultural Passport UI | — |
| 18 | Evaluation: 3–5 case study, Baseline vs Proposed (template chung) | Bảng kết quả |
| 19 | **BUFFER** — không thêm feature, chuẩn bị diagram/demo script | — |
| 20 | Hồ sơ + minh chứng: README, AI disclosure, Rule Base sources, Audit Log mẫu | Hồ sơ hoàn chỉnh |
| 21 | Quay video + demo (có pre-generated fallback) | Video + backup |

---

## 21. PHÂN CÔNG ĐỘI 3 NGƯỜI

**Member 1 — AI/Computer Vision:** Stable Diffusion, ControlNet, LoRA (optional), CLIP similarity, generation optimization.

**Member 2 — Knowledge + Governance:** heritage dataset, cultural research, Source-Grounded Rule Base (theo từng mẫu), documents, RAG (embedding, retrieval), source/provenance mapping.

**Member 3 — Governance Logic + Product:** LLM Planner, Validator, Constraint Engine, Streamlit UI, Cultural Passport, Audit Log, experiment management, demo.

**Nguyên tắc chung:** cả 3 phải hiểu toàn bộ pipeline — giám khảo có thể hỏi bất kỳ ai bất kỳ phần nào.

---

## 22. TEST CASE ĐỐI KHÁNG

| Test | Intent | Enum map | Rule Base (ví dụ BT001) | Kết quả |
|---|---|---|---|---|
| 1 — Allowed | "đổi màu nền" | `background` | modifiable | ALLOW |
| 2 — Blocked | "xóa hoa sen chính" | `core_motif` | preserve | BLOCK (protected_cultural_element, nguồn SRC001) |
| 3 — Blocked (theo item cụ thể) | "đổi ý nghĩa biểu tượng" (trên BT001) | `symbolic_element` | preserve (ở BT001) | BLOCK |
| 3b — Allowed (item khác) | "đổi ý nghĩa biểu tượng" (trên BT005) | `symbolic_element` | modifiable (ở BT005, khác nguồn) | ALLOW |
| 4 — Restricted (inconsistent) | "làm cho nó kỳ lạ hơn" | LLM trả nhãn khác nhau giữa 2 lần gọi | — | RESTRICT (inconsistent_classification) |
| 5 — Reimagine | "thiết kế lại bố cục" | `composition_layout` | modifiable | ALLOW + weight thấp hơn (Reimagine mode) |
| 6 — Multi-transformation hợp lệ (bug đã sửa) | "đổi màu nền và thay bố cục" | 2 item: `color_palette`, `composition_layout` | cả hai modifiable | **ALLOW cả hai** (không còn bị RESTRICT oan như thiết kế cũ) |

Test 3 và 3b minh chứng cụ thể nguyên tắc: cùng một category (`symbolic_element`) có thể cho kết quả khác nhau tùy heritage item, dựa trên nguồn tài liệu riêng của từng mẫu — không có rule cứng áp chung.

Test 6 minh chứng việc sửa lỗi logic quan trọng nhất của vòng review này: nhiều transformation hợp lệ trong một câu không còn bị nhầm là ambiguous chỉ vì số lượng nhãn ≥ 2.

---

## 23. RỦI RO VÀ CÁCH XỬ LÝ

| Rủi ro | Cách xử lý |
|---|---|
| Copyright dữ liệu | Ưu tiên nguồn public domain/có license rõ ràng; lưu provenance từng mẫu |
| LLM phân loại sai ngữ nghĩa (enum không đảm bảo đúng) | Cấp Rule Base context cho Planner + self-consistency check (2 lần gọi/item) + Validator fail-safe |
| Nhầm multi-transformation hợp lệ thành ambiguous (bug đã sửa) | Validator xử lý từng transformation item độc lập, không dùng số lượng nhãn làm proxy cho mơ hồ |
| Baseline/Proposed confound (prompt) | Dùng chung prompt template, chỉ khác constraint block |
| Baseline/Proposed confound (ControlNet weight) | Baseline dùng weight cố định đồng nhất; Proposed dùng weight thích ứng theo category — cả hai được định nghĩa tường minh |
| Threshold similarity tùy tiện | Không đặt ngưỡng đạt/không đạt; chỉ so sánh tương đối |
| RAG bị fallback hoàn toàn thành lookup | Go/No-Go chỉ áp dụng cho Rule Base retrieval, Evidence retrieval bắt buộc chạy thật |
| Rào cản prompt engineering với người dùng phổ thông | Guided UI (checkbox) là kênh chính, text tự do là mở rộng |
| Scope quá lớn | Danh sách "KHÔNG làm" (mục 24) + buffer 2 ngày mỗi tuần cuối |
| LLM lỗi JSON format khi demo | Retry 1 lần, fallback về `other_unclassified` nếu vẫn lỗi |

---

## 24. NHỮNG ĐIỀU KHÔNG LÀM TRONG 3 TUẦN

❌ React (nếu Streamlit đủ) · ❌ Mobile app · ❌ Authentication · ❌ Recommendation · ❌ Marketplace · ❌ Chatbot văn hóa riêng · ❌ Multi-language · ❌ Multi-heritage · ❌ Multi-product · ❌ Fine-tune model lớn / train foundation model · ❌ Human evaluation diện rộng · ❌ Dashboard analytics · ❌ User management · ❌ Payment · ❌ Thêm tầng LLM Critic/Judge để "vá" lỗi Planner.

---

## 25. DEMO SCRIPT (90–130 giây)

**0–15s:** Hiển thị họa tiết gốm Bát Tràng. *"Nếu AI có thể sáng tạo từ di sản, làm sao chúng ta đảm bảo AI không vô tình sáng tạo lại chính bản sắc của di sản?"*

**15–30s:** Generic AI tạo output. *"Đẹp, nhưng chúng ta biết gì về nguồn gốc?"*

**30–50s:** Mở hệ thống, chọn heritage. RAG hiển thị Origin/Meaning/Core Motif kèm nguồn.

**50–65s:** Chọn checkbox "đổi màu nền" (Preserve mode) → Generate. *(minh họa kênh chính — nhanh, không rủi ro)*

**65–80s:** Hiển thị Visual Similarity (tham khảo, không phải "đạt/không đạt").

**80–95s:** Chuyển sang Reimagine mode, chọn "thay đổi bố cục" → Generate, output biến đổi mạnh hơn rõ rệt.

**95–115s (khoảnh khắc quan trọng nhất):** Gõ vào ô text tự do: *"xóa hoa sen chính"*. LLM Planner phân loại vào `core_motif` (đã được cấp Rule Base context). Validator so khớp, phát hiện đây là preserve, chặn lại.
> *"Yêu cầu này tác động đến core_motif — yếu tố được xác định cần bảo tồn dựa trên nguồn SRC001. Hệ thống không thực hiện biến đổi này."*

**115–130s:** Mở Cultural Passport, hiển thị đầy đủ preserved/modified/similarity/sources. Kết:
> *"AI có thể sáng tạo từ di sản. Nhưng nguồn gốc của di sản không nên bị AI sáng tạo lại."*

---

## 26. CORE INNOVATION STATEMENT & PITCH

### Core Innovation Statement (dùng trong hồ sơ kỹ thuật)

> Chúng tôi đề xuất một pipeline AI có ràng buộc văn hóa, trong đó dữ liệu di sản đã được xác lập rule theo từng hiện vật cụ thể (không áp dụng rule chung chung) và có căn cứ nguồn tài liệu rõ ràng. Một LLM Planner được cấp ngữ cảnh Rule Base để diễn giải ý định người dùng thành nhãn cố định, kèm cơ chế phát hiện ý định mơ hồ; một Validator tất định thực hiện quyết định cuối cùng theo nguyên tắc mặc định từ chối (default-deny) khi không chắc chắn. Generative AI chỉ nhận chỉ thị đã qua kiểm soát này, với cường độ biến đổi được điều tiết theo chế độ sáng tạo do người dùng chọn. Mỗi output được gắn một hồ sơ provenance minh bạch, phân biệt rõ nguồn gốc di sản và phần sáng tạo của AI — cùng toàn bộ nhật ký quyết định có thể truy vết.

### One-line Pitch

> Tái sinh Di sản Số — nền tảng AI biến di sản Việt thành chất liệu sáng tạo cho thế hệ trẻ, với một lớp quản trị văn hóa (Cultural Governance Layer) đảm bảo AI chỉ được sáng tạo trong giới hạn có nguồn gốc và minh bạch.

### Ba từ khóa giá trị

**CREATE — LEARN — VERIFY**

---

## 27. KHẢ NĂNG MỞ RỘNG (ngoài phạm vi MVP)

| Phase | Nội dung |
|---|---|
| Phase 1 (MVP) | Họa tiết gốm Bát Tràng → T-shirt |
| Phase 2 | Mở rộng sản phẩm đầu ra (sticker, poster, wallpaper — cùng pipeline hình ảnh) |
| Phase 3 | Thổ cẩm, họa tiết làng nghề khác |
| Phase 4 | Kiến trúc, truyện dân gian |
| Phase 5 | Âm nhạc truyền thống (domain hoàn toàn khác, cần Cultural Knowledge Module riêng) |

Mỗi loại di sản mới có thể có Knowledge Module riêng nhưng dùng chung: Governance Layer, Validator logic, Visual Similarity Assessment, Cultural Passport, UI framework — không cần xây lại toàn bộ hệ thống.

---

*Tài liệu này tổng hợp toàn bộ các vòng review kỹ thuật và là bản đặc tả cuối cùng để team bắt đầu triển khai. Mọi thay đổi scope sau Ngày 1 cần được ghi nhận rõ và đánh giá tác động lên timeline.*
