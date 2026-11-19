# Trọng số LoRA dáng áo dài

LoRA là lớp nhỏ gắn thêm vào mô hình Stable Diffusion 1.5 để mô hình sinh được dáng áo dài. Thư mục này chứa hai bản đã huấn luyện.

| Thư mục | Cấu hình | Dùng trong sản phẩm |
|---|---|---|
| `aodai_r16_512/` | rank 16, ảnh 512x688 | có (mặc định, `generation/garment_lora.py`) |
| `aodai_r32_768/` | rank 32, ảnh 768x1032 | không (nền áo có sọc, chỉ giữ để đối chứng) |

## Giấy phép: chỉ dùng phi thương mại
Trọng số học từ 226 ảnh đã lọc của bộ VietFashion, theo giấy phép CC BY-NC 4.0 (chỉ dùng phi thương mại). Tác giả bộ dữ liệu đã đồng ý bằng email cho nhóm dùng. Không dùng các trọng số này vào mục đích thương mại.

Trích dẫn: Cao, Bui, Vo, Tran, Le. VietFashion: Benchmarking Sketch-Text Composed Image Retrieval for Cultural Outfits. ICMR 2026. doi:10.1145/3805622.3810590

Huấn luyện bằng `scripts/13_train_lora.py`. Mỗi thư mục có `config.json` ghi cấu hình và `train_log.csv` ghi đường loss.
