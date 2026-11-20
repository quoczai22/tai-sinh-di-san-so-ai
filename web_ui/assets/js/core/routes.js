// core/routes.js — BẢNG ĐỊNH TUYẾN: mỗi trang một dòng (mã, nhãn menu, tiêu đề ảnh bìa, view tải lười).
// Web chỉ dành cho người xem: Trang chủ, Studio (chọn hiện vật) và Kết quả (4 tà áo). Hồ sơ nghiệp vụ (kiểm định,
// thí nghiệm, thẩm định, Passport, BPMN, KPI) nằm trong dữ liệu, API và docs/finals — không đưa lên web.
// Thêm trang mới: thêm một dòng ở đây + một file views/<mã>.js có hàm render(args).
const CHAPTER = { 'Khám phá': '01' };
export const CHAPTER_NOTE = {};

export const ROUTES = [
    { group: 'Khám phá', id: 'library', label: 'Trang chủ', short: 'Trang chủ', icon: 'library', primary: true, load: () => import('../views/library.js'),
      title: 'Thư viện di sản', lede: 'Hoa văn trên gốm Bát Tràng, chọn lọc và ghi nguồn, làm chất liệu cho tà áo dài.' },
    { group: 'Khám phá', id: 'studio', label: 'Studio thiết kế', short: 'Studio', icon: 'studio', primary: true, load: () => import('../views/studio.js'),
      title: 'Studio thiết kế', lede: '' },
    // Trang Kết quả chỉ vào qua nút Tạo thiết kế, không nằm trong menu
    { group: 'Khám phá', id: 'result', label: 'Kết quả', short: 'Kết quả', icon: 'studio', hidden: true, load: () => import('../views/result.js'),
      title: 'Kết quả thiết kế', lede: 'Bốn thiết kế áo dài dệt từ hoa văn của hiện vật bạn chọn.' },
].map((r) => ({ ...r, chapter: CHAPTER[r.group] }));
