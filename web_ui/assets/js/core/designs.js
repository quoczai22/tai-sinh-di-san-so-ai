// core/designs.js — QUY TẮC CHỌN ẢNH của một thiết kế (Passport), dùng chung cho ảnh bìa, trang chủ, trang Kết quả.
// Trước đây mỗi file tự viết lại latestOf/PREF; gom về một chỗ để ba nơi luôn hiện cùng một ảnh.
// Ra: latestOf(d) ảnh mới nhất (bản hệ thống sửa nếu có), patternOf(d) ảnh hoa văn, byPref sắp theo trạng thái
//     duyệt, pickPassport(list) thiết kế tiêu biểu, fullImage() ảnh PNG gốc để tải xuống.
import * as data from './data.js';

// Thứ tự ưu tiên trạng thái duyệt khi chọn thiết kế tiêu biểu để trình bày
export const PREF = ['pending_expert_review', 'qa_warning', 'revision_requested', 'approved', 'qa_failed'];

export const latestOf = (d) => (d.latest_version_kind === 'system_repair' && d.repair_thumb ? d.repair_thumb : d.thumb);
export const patternOf = (d) => d.pattern_thumb || (d.thumb ? d.thumb.replace(/final_img2img\.webp$/, 'pattern.webp') : null);
// Đường dẫn ảnh để HIỂN THỊ. Thiết kế đã có bản chỉnh sửa của người dùng thì vẫn hiện ảnh hệ thống tạo (gateway không phục vụ
// ảnh người dùng tải lên, để ảnh đó không bị công khai); trang Kết quả đánh dấu "Có bản chỉnh sửa".
export const shownPath = (d) => (d.latest_version_kind === 'human_edit' ? (d.repair_path || d.final_path) : (d.latest_path || d.final_path));
export const assetUrl = (path) => !path ? '' : (/^(https?:)?\/\//.test(path) || path.startsWith('/') ? path : './' + path);
export const byPref = (a, b) => (PREF.indexOf(a.approval.status) - PREF.indexOf(b.approval.status)) || a.passport_id.localeCompare(b.passport_id);

export function pickPassport(list) {
    return [...list].filter((d) => d.thumb).sort(byPref)[0];
}

// Ảnh gốc đầy đủ của thiết kế. Chế độ trực tiếp: tệp PNG từ máy chủ. Chế độ trình diễn: bản PNG gốc scripts/demo/export_demo_data.py
// chép vào assets/images/variants/<mã hiện vật>_V<số>_aodai.png (thiết kế đã được hệ thống sửa thì chỉ có bản WebP nén).
export function fullImage(d, heritageId, fallback) {
    if (data.isLive() || latestOf(d) !== d.thumb) return fallback;
    if (d.full_image) return assetUrl(d.full_image);                  // bộ dành riêng cho trang Kết quả (xuất bằng --only-result)
    return `./assets/images/variants/${encodeURIComponent(heritageId)}_V${d.passport_id.split('-V').pop()}_aodai.png`;
}
