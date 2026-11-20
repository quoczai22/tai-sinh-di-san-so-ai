# Deploy `web_ui` lên Vercel

Trong **Project Settings → General → Root Directory** trên Vercel, đặt **`web_ui`**.

- Các file tĩnh (`index.html`, `assets/`, `components/`) và dữ liệu demo thật (`assets/data/demo_variants.json`) được phục vụ trực tiếp.
- Các hàm cổng điều phối failover (`api/generate.js`, `api/status.js`, `api/warmup.js`, `api/media.js`, `api/heritage.js`, `api/audit.js`, `api/health.js`) tự động ánh xạ vào `/api/*`.
- `DH_API_BASE` mặc định là `/api` (có thể ghi đè khi chạy local bằng `?api=http://127.0.0.1:8000` hoặc `localStorage.setItem('DH_API_BASE', ...)`).

Hướng dẫn đầy đủ về sơ đồ kiến trúc, biến môi trường (`MODAL_URL`, `MODAL_KEY`, `HF_SPACE_URL`, `HF_TOKEN`, `MODAL_TIMEOUT_MS`, `RATE_LIMIT_PER_HOUR`), lệnh deploy Modal/HF Space và cách chuyển đổi dự phòng nằm tại [`../docs/DEPLOY.md`](../docs/DEPLOY.md).
