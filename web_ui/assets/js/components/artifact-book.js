// components/artifact-book.js — SỔ HOA VĂN của một hiện vật (Studio, bước 1: hiểu đầu vào trước khi tạo).
// Nút "Xem ý nghĩa hoa văn" mở một cuốn sổ hai trang nổi trên trang hiện tại (không chuyển trang):
//   · trang trái: ảnh tĩnh của hiện vật (ảnh tách nền xuất từ data/heritage/cutouts), tên và dáng bình;
//   · trang phải: đoạn mô tả hoa văn và ý nghĩa (motif_text), nguồn ảnh và giấy phép.
// Đóng bằng dấu X, phím Esc hoặc bấm ra ngoài; giữ tiêu điểm bàn phím trong sổ và trả về nút đã bấm.
// Dữ liệu: item.info (khối artifact_info trong data/heritage/metadata.json) và item.provenance.
// Chỉ hiện những gì người xem cần; căn cứ biên soạn (nguồn từng ý nghĩa, đối chiếu bảo tàng) nằm trong dữ liệu và docs.
// Ra: bookButton(item) → nút mở sổ; openArtifactBook(item, opener).
import { h } from '../core/dom.js';
import { icon } from '../core/icons.js';

const DATASET_DOI = 'https://doi.org/10.17632/jr23fnrvx2.1';
const LICENSE_URL = 'https://creativecommons.org/licenses/by/4.0/deed.vi';

// Chỉ mở liên kết http(s); địa chỉ khác hiện thành chữ thường
function outLink(url, text, cls = 'bk-link') {
    let safe = '';
    try { const u = new URL(url); if (['http:', 'https:'].includes(u.protocol)) safe = u.href; } catch { /* bỏ qua */ }
    if (!safe) return h('span', { class: cls }, text);
    return h('a', { class: cls, href: safe, target: '_blank', rel: 'noopener noreferrer' }, text, icon('external'));
}

function leftPage(item) {
    return h('section', { class: 'bk-page bk-left', 'aria-label': 'Ảnh hiện vật' },
        h('p', { class: 'bk-kicker' }, 'Hiện vật'),
        h('figure', { class: 'bk-figure' },
            h('div', { class: 'bk-frame' }, h('img', { src: item.image, alt: item.name })),
            h('figcaption', {},
                h('span', { class: 'bk-name' }, item.name),
                item.info?.form ? h('span', { class: 'bk-cap' }, item.info.form) : null)),
        h('p', { class: 'bk-folio', 'aria-hidden': 'true' }, 'i'));
}

function rightPage(item) {
    const info = item.info || {};
    const p = item.provenance || {};
    return h('section', { class: 'bk-page bk-right', 'aria-label': 'Hoa văn và nguồn ảnh' },
        h('p', { class: 'bk-kicker' }, 'Hoa văn và ý nghĩa'),
        h('p', { class: 'bk-text' }, info.motifText || 'Chưa có mô tả hoa văn cho hiện vật này.'),
        h('div', { class: 'bk-block' },
            h('p', { class: 'bk-h' }, 'Nguồn ảnh'),
            h('p', {}, 'Bộ dữ liệu LR3D-CULT2 (Nguyen và cộng sự, FPT University), Mendeley Data, ',
                outLink(p.sourceUrl || DATASET_DOI, 'DOI 10.17632/jr23fnrvx2.1'), '.'),
            h('p', {}, 'Giấy phép: ', outLink(LICENSE_URL, 'CC BY 4.0'), '.')),
        h('p', { class: 'bk-folio', 'aria-hidden': 'true' }, 'ii'));
}

export function openArtifactBook(item, opener) {
    // Gỡ sổ khỏi trang và trả tiêu điểm cho nút đã mở nó
    const remove = () => {
        overlay.remove();
        document.body.classList.remove('book-open');
        opener?.focus();
    };
    // Đóng sổ: chạy hiệu ứng khép sách (class is-closing) rồi mới gỡ; tắt hiệu ứng thì gỡ ngay
    const close = () => {
        if (overlay.classList.contains('is-closing')) return;
        document.removeEventListener('keydown', onKey);
        if (matchMedia('(prefers-reduced-motion: reduce)').matches) { remove(); return; }
        overlay.classList.add('is-closing');
        overlay.addEventListener('animationend', (e) => { if (e.target === overlay) remove(); });
        setTimeout(remove, 1200);                                     // phòng khi sự kiện animationend không tới
    };
    const closeBtn = h('button', { class: 'bk-close', type: 'button', 'aria-label': 'Đóng sổ' }, icon('close'));
    closeBtn.addEventListener('click', close);
    // Dấu X nằm ngoài phần cuộn của sổ (màn hẹp cuộn cả cuốn sổ) để luôn nhìn thấy
    const book = h('div', { class: 'bk-book' }, leftPage(item), rightPage(item));
    const overlay = h('div', { class: 'book-overlay', role: 'dialog', 'aria-modal': 'true', 'aria-label': `Sổ hoa văn: ${item.name}` },
        h('div', { class: 'bk-wrap' }, h('div', { class: 'bk-sheet' }, book), closeBtn));
    overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });
    const onKey = (e) => {
        if (e.key === 'Escape') { close(); return; }
        if (e.key !== 'Tab') return;                                    // giữ tiêu điểm bàn phím trong sổ
        const f = [...overlay.querySelectorAll('a[href], button')];
        const i = f.indexOf(document.activeElement);
        const next = e.shiftKey ? (i <= 0 ? f.length - 1 : i - 1) : (i + 1) % f.length;
        e.preventDefault();
        f[next].focus();
    };
    document.body.classList.add('book-open');
    document.getElementById('overlay-root').append(overlay);
    document.addEventListener('keydown', onKey);
    closeBtn.focus({ preventScroll: true });
}

export function bookButton(item) {
    const btn = h('button', { class: 'book-btn', type: 'button', 'aria-haspopup': 'dialog' }, icon('book'), 'Xem ý nghĩa hoa văn');
    btn.addEventListener('click', () => openArtifactBook(item, btn));
    return btn;
}
