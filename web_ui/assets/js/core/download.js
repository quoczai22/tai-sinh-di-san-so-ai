// core/download.js — TẢI ẢNH THIẾT KẾ về máy (nút Tải xuống ở cửa sổ phóng to và nút Tải toàn bộ ở trang Kết quả).
// Ra: downloadImage(src, tên, { edited }) → luôn lưu PNG có in nhãn "Hỗ trợ bởi AI" ở góc dưới trái; nếu edited thì thêm nhãn
// "Đã chỉnh sửa" ở góc trên phải (như trên giao diện). Không tải được thì mở ảnh ở thẻ mới.
import { h } from './dom.js';

// Nhãn bắt buộc cho ảnh do AI hỗ trợ tạo (YC3): hiện trên giao diện (components/badges.js) và in lên file tải về.
export const AI_LABEL = 'Hỗ trợ bởi AI';
export const EDITED_LABEL = 'Đã chỉnh sửa';          // thêm khi thiết kế đã có bản người dùng chỉnh sửa (components/badges.js editedMark)

// Vẽ ảnh lên canvas rồi in nhãn AI ở góc dưới trái (và nhãn Đã chỉnh sửa ở góc trên phải nếu edited), trả về PNG.
// Cũng đổi mọi định dạng (ví dụ WebP) sang PNG.
async function toLabeledPng(blob, edited = false) {
    const bitmap = await createImageBitmap(blob);
    const canvas = document.createElement('canvas');
    canvas.width = bitmap.width;
    canvas.height = bitmap.height;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(bitmap, 0, 0);
    // Cỡ chữ theo chiều rộng ảnh, tối thiểu 12px để vẫn đọc được trên ảnh nhỏ
    const fontPx = Math.max(12, Math.round(bitmap.width * 0.03));
    const padX = Math.round(fontPx * 0.7), padY = Math.round(fontPx * 0.45), margin = Math.round(fontPx * 0.8);
    ctx.font = `600 ${fontPx}px system-ui, "Segoe UI", sans-serif`;
    const boxW = Math.round(ctx.measureText(AI_LABEL).width) + padX * 2, boxH = fontPx + padY * 2;
    const x = margin, y = bitmap.height - margin - boxH;
    ctx.fillStyle = 'rgba(252, 251, 247, 0.92)';
    ctx.fillRect(x, y, boxW, boxH);
    ctx.fillStyle = '#1d2a36';
    ctx.textBaseline = 'middle';
    ctx.fillText(AI_LABEL, x + padX, y + boxH / 2);
    if (edited) {                                           // góc trên phải, nền xanh chữ trắng như nhãn trên giao diện
        ctx.font = `700 ${fontPx}px system-ui, "Segoe UI", sans-serif`;
        const w = Math.round(ctx.measureText(EDITED_LABEL).width) + padX * 2;
        const ex = bitmap.width - margin - w;
        ctx.fillStyle = '#24508A';
        ctx.fillRect(ex, margin, w, boxH);
        ctx.fillStyle = '#ffffff';
        ctx.fillText(EDITED_LABEL, ex + padX, margin + boxH / 2);
    }
    return new Promise((resolve, reject) => canvas.toBlob((b) => (b ? resolve(b) : reject(new Error('toBlob'))), 'image/png'));
}

// Tải ảnh về máy: lấy ảnh dạng blob rồi bấm một liên kết download (thuộc tính download không chạy với ảnh khác nguồn).
// File tải về luôn là PNG có nhãn AI. Nếu không lấy được ảnh thì mở ảnh ở thẻ mới (khi đó ảnh chưa có nhãn in).
export async function downloadImage(src, filename, { edited = false } = {}) {
    try {
        const res = await fetch(src);
        if (!res.ok) throw new Error(res.status);
        const blob = await toLabeledPng(await res.blob(), edited);   // luôn là PNG có nhãn AI, thêm nhãn Đã chỉnh sửa nếu edited
        const url = URL.createObjectURL(blob);
        const a = h('a', { href: url, download: `${filename}.png` });
        document.body.append(a);
        a.click();
        a.remove();
        setTimeout(() => URL.revokeObjectURL(url), 4000);
    } catch {
        window.open(src, '_blank', 'noopener');
    }
}
