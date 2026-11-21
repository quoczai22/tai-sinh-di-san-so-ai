// core/designs.js — QUY TẮC CHỌN ẢNH của một thiết kế (Passport), dùng chung cho ảnh bìa, trang chủ, trang Kết quả.
// Trước đây mỗi file tự viết lại latestOf/PREF; gom về một chỗ để ba nơi luôn hiện cùng một ảnh.
// Ra: latestOf(d) ảnh mới nhất (bản hệ thống sửa nếu có), patternOf(d) ảnh hoa văn, byPref sắp theo trạng thái
//     duyệt, pickPassport(list) thiết kế tiêu biểu, fullImage() ảnh PNG gốc để tải xuống.
import * as data from './data.js';

// Thứ tự ưu tiên trạng thái duyệt khi chọn thiết kế tiêu biểu để trình bày
export const PREF = ['pending_expert_review', 'qa_warning', 'revision_requested', 'approved', 'qa_failed'];

export const latestOf = (d) => (d.latest_version_kind === 'system_repair' && d.repair_thumb ? d.repair_thumb : d.thumb);
export const patternOf = (d) => (d.thumb ? d.thumb.replace(/final_img2img\.webp$/, 'pattern.webp') : null);
export const byPref = (a, b) => (PREF.indexOf(a.approval.status) - PREF.indexOf(b.approval.status)) || a.passport_id.localeCompare(b.passport_id);

export function pickPassport(list) {
    return [...list].filter((d) => d.thumb).sort(byPref)[0];
}

// Ảnh gốc đầy đủ của thiết kế. Chế độ trực tiếp: tệp PNG từ máy chủ. Chế độ trình diễn: bản PNG gốc scripts/11_export_demo_data.py
// chép vào assets/images/variants/<mã hiện vật>_V<số>_aodai.png (thiết kế đã được hệ thống sửa thì chỉ có bản WebP nén).
export function fullImage(d, heritageId, fallback) {
    if (data.isLive() || latestOf(d) !== d.thumb) return fallback;
    return `./assets/images/variants/${encodeURIComponent(heritageId)}_V${d.passport_id.split('-V').pop()}_aodai.png`;
}
