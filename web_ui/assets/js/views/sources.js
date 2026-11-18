import { fmt, h, icon } from '../lib/dom.js';
import * as data from '../lib/data.js';
import { RIGHTS, decisionChip, externalLink, rightsChip, section } from '../lib/ui.js';
import { openArtifact } from './library.js';

function permissionLetter(item) {
    const p = item.provenance || {};
    return `Kính gửi ${p.holder || 'Quý đơn vị'},

Chúng tôi là nhóm sinh viên dự thi Cuộc thi Sáng tạo trẻ Quốc gia về Trí tuệ nhân tạo năm 2026 (Bảng C) với dự án phi thương mại "Tái Sinh Di Sản Số": công cụ đưa hoa văn gốm Bát Tràng lên thiết kế áo dài.

Chúng tôi đã dùng ảnh sản phẩm "${item.name}" tại địa chỉ:
${p.sourceUrl || '(đường dẫn)'}
làm ảnh tham chiếu đầu vào cho mô hình (hệ thống trích đường nét hoa văn, không phân phối lại ảnh gốc).

Chúng tôi trân trọng đề nghị Quý đơn vị cho phép:
1. Dùng ảnh trên cho mục đích nghiên cứu, thi đấu và trình diễn phi thương mại;
2. Ghi công theo dạng: "Ảnh: ${p.holder || '[tên đơn vị]'}" kèm đường dẫn nguồn.

Nếu Quý đơn vị không đồng ý, chúng tôi sẽ gỡ ảnh và các thiết kế liên quan khỏi bản trình diễn.

Trân trọng,
[Họ tên, trường, số điện thoại, email]`;
}

export async function render() {
    const { items, selection_criteria: criteria } = await data.heritage();
    const active = items.filter((i) => i.status === 'active');
    const pending = active.filter((i) => !['public_domain', 'open_license', 'permission_granted', 'own_work'].includes(i.provenance?.rightsStatus));
    const fields = ['Tên', 'URL nguồn', 'Đơn vị lưu giữ', 'Tác giả ảnh', 'Quyền', 'Giấy phép', 'Ghi công', 'Ngày thu thập', 'Phiên bản dữ liệu'];
    return h('div', {},
        section('Danh mục nguồn và giấy phép',
            'Mỗi dòng là một hiện vật. Ô đỏ là trường còn thiếu theo yêu cầu của Ban tổ chức; hệ thống không tự điền những trường này.',
            h('div', { class: 'table-wrap' }, h('table', { class: 'data' },
                h('thead', {}, h('tr', {}, h('th', {}, 'Mã'), fields.map((f) => h('th', {}, f)), h('th', {}, 'Đủ trường'), h('th', {}, 'Xuất bản'))),
                h('tbody', {}, items.map((it) => {
                    const p = it.provenance || {};
                    const cell = (v, render) => h('td', { class: v ? 'small' : 'small missing', style: v ? null : { color: 'var(--fail)' } }, v ? (render ? render(v) : v) : 'Thiếu');
                    return h('tr', {},
                        h('td', {}, h('button', { class: 'link-btn', onclick: () => openArtifact(it, criteria) }, it.code), it.status === 'retired' ? h('div', { class: 'muted small' }, 'ngừng dùng') : null),
                        h('td', { class: 'small' }, it.name),
                        cell(p.sourceUrl, (v) => externalLink(v)),
                        cell(p.holder), cell(p.author),
                        h('td', {}, rightsChip(p.rightsStatus)),
                        cell(p.license), cell(p.attribution),
                        cell(p.collectedOn || null),
                        cell(p.dataVersion, (v) => h('span', { class: 'hash' }, v)),
                        h('td', { class: 'num' }, `${it.completeness.filled}/${it.completeness.total}`),
                        h('td', {}, decisionChip(it.rights?.publish_public?.allowed ? 'PASS' : 'FAIL')));
                }))))),
        section('Việc còn phải làm', pending.length ? `${pending.length} hiện vật đang dùng chưa có căn cứ quyền sử dụng. Thiết kế từ các hiện vật này chỉ được trình diễn phi thương mại, kèm nhãn và ghi nguồn.` : 'Mọi hiện vật đang dùng đều có căn cứ quyền sử dụng.',
            h('div', { class: 'stack' }, pending.map((it) => {
                const letter = permissionLetter(it);
                return h('div', { class: 'panel stack' },
                    h('div', { class: 'row spread' }, h('b', {}, `${it.code} ${it.name}`), rightsChip(it.provenance?.rightsStatus)),
                    h('details', {}, h('summary', {}, 'Thư đề nghị cấp phép (bản soạn sẵn)'), h('pre', { class: 'small', style: { whiteSpace: 'pre-wrap', background: 'var(--porcelain-2)', padding: '12px', borderRadius: '8px' } }, letter)),
                    h('div', { class: 'row' }, h('button', { class: 'btn small', onclick: async () => {
                        try { await navigator.clipboard.writeText(letter); } catch { /* bỏ qua */ }
                    } }, 'Sao chép thư'), h('span', { class: 'muted small' }, 'Sau khi gửi: cập nhật permission_request trong data/heritage/metadata.json (ngày gửi, kênh, phản hồi).')));
            }))),
        section('Quy tắc của cổng quyền sử dụng', 'Mượn nguyên tắc "kiểm soát tại cổng, do hệ thống thực thi" từ kiến trúc quy trình mua hàng: quyền quyết định phạm vi được dùng, không chặn thử nghiệm nội bộ.',
            h('div', { class: 'table-wrap' }, h('table', { class: 'data' },
                h('thead', {}, h('tr', {}, ['Tình trạng', 'Thử nghiệm', 'Trình diễn', 'Xuất bản', 'Thương mại'].map((t) => h('th', {}, t)))),
                h('tbody', {}, Object.entries(RIGHTS).map(([k, r]) => {
                    const ok = ['public_domain', 'open_license', 'permission_granted', 'own_work'].includes(k);
                    const denied = k === 'permission_denied';
                    return h('tr', {}, h('td', {}, r.text),
                        h('td', {}, decisionChip(denied ? 'FAIL' : ok ? 'PASS' : 'WARN')),
                        h('td', {}, decisionChip(denied ? 'FAIL' : ok ? 'PASS' : 'WARN')),
                        h('td', {}, decisionChip(ok ? 'PASS' : 'FAIL')),
                        h('td', {}, decisionChip(['public_domain', 'own_work'].includes(k) ? 'PASS' : ['open_license', 'permission_granted'].includes(k) ? 'WARN' : 'FAIL')));
                }))))),
        h('p', { class: 'muted small section' }, icon('info'), ' Mọi ảnh xuất từ hệ thống mang nhãn "Thiết kế hỗ trợ bởi AI" kèm mã Passport, và siêu dữ liệu PNG ghi nguồn hiện vật. ',
            `Dữ liệu xuất lúc ${fmt.date(data.meta()?.generated_at)}.`));
}
