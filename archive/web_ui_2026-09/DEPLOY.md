# Deploy web_ui

Có thể deploy từ repository root bằng Vercel. `vercel.json` đã chuyển `/` tới `web_ui/index.html` và giữ nguyên đường dẫn assets/components.

Nếu Vercel đặt **Root Directory** là `web_ui`, không cần thêm build command; chọn output directory là `.`.

Sau khi API GPU có domain production, sửa `web_ui/assets/js/config.js`:

```js
window.DH_API_BASE = "https://api.example.com";
```
