// core/download.js — TẢI ẢNH THIẾT KẾ về máy (nút Tải xuống ở cửa sổ phóng to và nút Tải toàn bộ ở trang Kết quả).
// Ra: downloadImage(src, tên) → luôn lưu PNG/JPEG, không bao giờ WebP; không tải được thì mở ảnh ở thẻ mới.
import { h } from './dom.js';

// Đổi ảnh bất kỳ (ví dụ WebP) sang PNG bằng canvas, để file người xem nhận luôn là định dạng ảnh phổ biến.
async function toPng(blob) {
    const bitmap = await createImageBitmap(blob);
    const canvas = document.createElement('canvas');
    canvas.width = bitmap.width;
    canvas.height = bitmap.height;
    canvas.getContext('2d').drawImage(bitmap, 0, 0);
    return new Promise((resolve, reject) => canvas.toBlob((b) => (b ? resolve(b) : reject(new Error('toBlob'))), 'image/png'));
}

// Tải ảnh về máy: lấy ảnh dạng blob rồi bấm một liên kết download (thuộc tính download không chạy với ảnh khác nguồn).
// File tải về luôn là PNG hoặc JPEG, không bao giờ là WebP. Nếu không lấy được thì mở ảnh ở thẻ mới để người xem tự lưu.
export async function downloadImage(src, filename) {
    try {
        const res = await fetch(src);
        if (!res.ok) throw new Error(res.status);
        let blob = await res.blob();
        // Đuôi file: theo loại ảnh máy chủ báo; nếu không có thì lấy theo đuôi trong đường dẫn ảnh
        let ext = { 'image/png': 'png', 'image/webp': 'webp', 'image/jpeg': 'jpg' }[blob.type]
            || (decodeURIComponent(src).match(/\.(png|webp|jpe?g)(?:$|[?&#])/i)?.[1] || 'png').toLowerCase();
        if (ext === 'webp') { blob = await toPng(blob); ext = 'png'; }
        const url = URL.createObjectURL(blob);
        const a = h('a', { href: url, download: `${filename}.${ext}` });
        document.body.append(a);
        a.click();
        a.remove();
        setTimeout(() => URL.revokeObjectURL(url), 4000);
    } catch {
        window.open(src, '_blank', 'noopener');
    }
}
