// Địa chỉ API GPU. Để trống hoặc không gọi được → giao diện tự chuyển sang chế độ
// trình diễn, đọc dữ liệu THẬT đã sinh sẵn trong ./data/ (không có số giả).
// Khi deploy: đặt window.DH_API_BASE trỏ tới cổng API (ví dụ Vercel /api hoặc Modal).
window.DH_API_BASE = window.DH_API_BASE ?? (['127.0.0.1', 'localhost'].includes(location.hostname) ? 'http://127.0.0.1:8000' : '/api/live');
