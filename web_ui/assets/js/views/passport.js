import { downloadJson, fmt, h, icon, toast } from '../lib/dom.js';
import * as data from '../lib/data.js';
import { ACTOR, APPROVAL, actorMark, approvalChip, artifactNodes, chain, decisionChip, externalLink, kv, rightsChip, section, stateBox } from '../lib/ui.js';

const KIND = { ai_generated: 'AI sinh', system_repair: 'Hệ thống sửa (khoá họa tiết)', human_edit: 'Con người chỉnh sửa' };
function eventLabel(t) {
    if (t.event.startsWith('approval:')) return `Trạng thái: ${APPROVAL[t.event.slice(9)]?.text || t.event.slice(9)}`;
    if (t.event.startsWith('version:')) return `Phiên bản mới: ${KIND[t.event.slice(8)] || t.event.slice(8)}`;
    return { quality_gate: 'Ghi kết quả cổng chất lượng', expert_review: 'Ghi phiếu thẩm định chuyên gia', published: 'Xuất bản' }[t.event] || t.label;
}
const ACTION = { demo_display: 'Trình diễn phi thương mại', publish_public: 'Xuất bản công khai', commercial_use: 'Thương mại' };

function list(passports) {
    return section('Tất cả Design Passport', `${passports.length} hồ sơ. Mỗi thiết kế có một Passport riêng; mã đi suốt từ hiện vật tới bản xuất.`,
        h('div', { class: 'table-wrap' }, h('table', { class: 'data' },
            h('thead', {}, h('tr', {}, ['Passport', 'Hiện vật', 'Phiên bản', 'Kiểm định', 'Trạng thái', 'Thẩm định', 'Chỉnh sửa'].map((t) => h('th', {}, t)))),
            h('tbody', {}, passports.map((p) => h('tr', {},
                h('td', {}, h('a', { href: `#/passport/${p.passport_id}` }, p.passport_id)),
                h('td', {}, p.heritage_name),
                h('td', {}, `${p.versions} (${KIND[p.latest_version_kind] || p.latest_version_kind})`),
                h('td', {}, decisionChip(p.quality_decision)),
                h('td', {}, approvalChip(p.approval.status)),
                h('td', { class: 'num' }, p.reviews), h('td', { class: 'num' }, p.edits)))))));
}

function editForm(p) {
    if (!data.isLive()) {
        return h('p', { class: 'note' }, 'Ghi chỉnh sửa thủ công cần máy chủ API: tải bản đã sửa lên, hệ thống băm tệp, tạo phiên bản mới gắn với phiên bản cha, chạy lại cổng G3 trên bản sửa rồi mới đưa về hàng đợi QC hoặc thẩm định.');
    }
    const file = h('input', { type: 'file', accept: 'image/png,image/jpeg' });
    const editor = h('input', { placeholder: 'Ví dụ: TK01', maxlength: 24 });
    const role = h('select', {}, h('option', { value: 'designer' }, 'Nhà thiết kế'), h('option', { value: 'qc_officer' }, 'QC'));
    const tool = h('input', { placeholder: 'Ví dụ: Photoshop 2025, chỉnh tay', maxlength: 80 });
    const desc = h('textarea', { placeholder: 'Sửa gì, ở vùng nào, vì sao', maxlength: 500 });
    const btn = h('button', { class: 'btn primary', type: 'button', onclick: async () => {
        const f = file.files[0];
        if (!f) { toast('Chọn tệp ảnh đã chỉnh sửa.'); return; }
        if (f.size > 8 * 1024 * 1024) { toast('Ảnh vượt 8 MB.'); return; }
        btn.disabled = true;
        try {
            const b64 = await new Promise((res, rej) => { const r = new FileReader(); r.onload = () => res(String(r.result)); r.onerror = rej; r.readAsDataURL(f); });
            const res = await data.submitEdit(p.passport_id, { editor_id: editor.value.trim(), editor_role: role.value, tool: tool.value.trim(), description: desc.value.trim(), image_png_base64: b64 });
            const verdict = res && res.quality_decision ? ` Cổng G3 trên bản sửa: ${res.quality_decision}.` : ' Chưa chạy được G3, QC sẽ xem thủ công.';
            toast(`Đã ghi bản sửa thành phiên bản mới.${verdict}`);
            window.dispatchEvent(new HashChangeEvent('hashchange'));
        } catch (err) { toast(err.message); btn.disabled = false; }
    } }, 'Ghi chỉnh sửa');
    return h('form', { class: 'panel stack', onsubmit: (e) => e.preventDefault() },
        h('div', { class: 'grid cols-3' }, h('label', { class: 'field' }, 'Mã người sửa', editor), h('label', { class: 'field' }, 'Vai trò', role), h('label', { class: 'field' }, 'Công cụ', tool)),
        h('label', { class: 'field' }, 'Mô tả chỉnh sửa', desc), h('label', { class: 'field' }, 'Tệp sau khi sửa', file), btn);
}

async function detail(pid) {
    const p = await data.passport(pid);
    data.audit('passport_viewed', { step: 5, passport_id: pid });
    const latest = p.versions[p.versions.length - 1];
    const latestArt = p.artifacts.find((a) => a.path === latest?.path);
    const g = p.generation || {};
    const q = p.quality || {};
    const integ = p.integrity || {};
    const exportBtn = data.isLive()
        ? h('a', { class: 'btn primary', href: data.exportUrl(p.passport_id) }, icon('download'), 'Tải ảnh kèm nhãn AI')
        : h('button', { class: 'btn primary', onclick: () => downloadJson(`${p.passport_id}.json`, p) }, icon('download'), 'Tải Passport (.json)');
    return h('div', {},
        h('div', { class: 'passport-head' },
            h('div', { class: 'hero-img' }, h('img', { src: data.media(latestArt, latestArt?.display), alt: `Thiết kế ${p.passport_id}` })),
            h('div', { class: 'stack' },
                h('div', { class: 'pid' }, p.passport_id),
                h('div', { class: 'row' }, approvalChip(p.approval.status), h('span', { class: 'chip info' }, p.ai_disclosure.label), rightsChip(p.heritage.rights_status)),
                kv([
                    ['Hiện vật gốc', h('span', {}, `${p.heritage.code} ${p.heritage.name}`)],
                    ['Mã thiết kế', p.design_id],
                    ['Tạo lúc', fmt.date(p.created_at)],
                    ['Phiên bản hiện hành', latest ? `v${latest.version}, ${KIND[latest.kind] || latest.kind}` : '—'],
                    ['Lý do trạng thái', p.approval.reason],
                ]),
                h('div', { class: integ.ok ? 'note' : 'note warn' }, integ.ok
                    ? `Kiểm tra toàn vẹn: hợp lệ. ${integ.ledger_entries} sự kiện trong chuỗi băm, ${integ.files_checked} tệp khớp SHA-256.`
                    : `Kiểm tra toàn vẹn phát hiện vấn đề: ${(integ.problems || []).join('; ')}`),
                h('div', { class: 'row' }, exportBtn, h('a', { class: 'btn', href: `#/review/${p.passport_id}` }, 'Mở trong Thẩm định')))),
        section('Chuỗi truy vết', 'Từ ảnh hiện vật tới thiết kế cuối. Ký hiệu cho biết bước do AI, hệ thống tất định hay con người thực hiện.', chain(artifactNodes(p))),
        section('Ai làm gì', 'Phân định bắt buộc trong mọi Passport.',
            h('div', { class: 'steps-split' }, ['ai', 'system', 'human'].map((t) => h('div', { class: 'panel' },
                h('h3', { class: 'row' }, actorMark(t), ACTOR[t]),
                h('ul', {}, p.process_steps.filter((s) => s.actor_type === t).map((s) => h('li', {}, s.label, s.tool ? h('span', { class: 'muted small' }, ` (${s.tool})`) : null))),
                t === 'human' && !p.reviews.length ? h('p', { class: 'muted small' }, 'Chưa có thẩm định chuyên gia.') : null)))),
        h('div', { class: 'grid cols-2 section' },
            h('div', { class: 'panel' }, h('h3', {}, 'Nguồn và giấy phép'), kv([
                ['Nguồn', p.heritage.source_title], ['URL', p.heritage.source_url ? externalLink(p.heritage.source_url) : null, !p.heritage.source_url],
                ['Đơn vị lưu giữ', p.heritage.holder], ['Tác giả ảnh', p.heritage.author, !p.heritage.author],
                ['Giấy phép', p.heritage.license, !p.heritage.license], ['Ghi công', p.heritage.attribution],
                ['Phiên bản dữ liệu', p.heritage.registry_data_version], ['SHA-256 ảnh gốc', h('span', { class: 'hash' }, fmt.hash(p.heritage.source_image_sha256, 16))],
            ])),
            h('div', { class: 'panel' }, h('h3', {}, 'Mô hình và tham số'), kv([
                ['Mô hình sinh', g.models?.sd], ['ControlNet', g.models?.controlnet],
                ['Phiên bản thư viện', `torch ${g.versions?.torch}, diffusers ${g.versions?.diffusers}`], ['GPU', g.versions?.gpu],
                ['Seed', g.seed], ['Trọng số ControlNet', fmt.num(g.controlnet?.conditioning_scale, 2)],
                ['Canny', `${g.controlnet?.canny_low}/${g.controlnet?.canny_high}, bóc đường bao ${g.controlnet?.outline_erode_px} px`],
                ['Bố cục', `${g.layout?.label} (${g.layout?.selected_by === 'clip_auto' ? 'CLIP tự chọn' : 'cố định'})`],
                ['img2img', `strength ${fmt.num(g.polish_img2img?.strength, 2)}, ${g.polish_img2img?.steps} bước`],
                ['Prompt', h('span', { class: 'small' }, g.prompt)],
            ]))),
        section('Phiên bản', 'Mỗi phiên bản giữ mã băm của chính nó và của phiên bản cha. Phiên bản cũ không bao giờ bị ghi đè.',
            h('div', { class: 'table-wrap' }, h('table', { class: 'data' },
                h('thead', {}, h('tr', {}, ['Phiên bản', 'Loại', 'Người/hệ thống tạo', 'Thời điểm', 'SHA-256', 'Phiên bản cha'].map((t) => h('th', {}, t)))),
                h('tbody', {}, p.versions.map((v) => h('tr', {}, h('td', {}, `v${v.version}`), h('td', {}, KIND[v.kind] || v.kind),
                    h('td', {}, v.created_by), h('td', {}, fmt.date(v.created_at)), h('td', { class: 'hash' }, fmt.hash(v.sha256, 12)),
                    h('td', { class: 'hash' }, v.parent_version ? `v${v.parent_version} (${fmt.hash(v.parent_sha256, 8)})` : 'gốc'))))))),
        section('Chỉnh sửa thủ công', p.edits.length ? null : 'Chưa có chỉnh sửa thủ công nào được ghi nhận cho thiết kế này.',
            p.edits.length ? h('div', { class: 'table-wrap' }, h('table', { class: 'data' },
                h('thead', {}, h('tr', {}, ['Mã', 'Người sửa', 'Thời điểm', 'Nội dung', 'Công cụ', 'Trước', 'Sau'].map((t) => h('th', {}, t)))),
                h('tbody', {}, p.edits.map((e) => h('tr', {}, h('td', {}, e.edit_id), h('td', {}, `${e.editor_id} (${e.editor_role})`), h('td', {}, fmt.date(e.at)),
                    h('td', {}, e.description), h('td', {}, e.tool), h('td', { class: 'hash' }, fmt.hash(e.before_sha256, 8)), h('td', { class: 'hash' }, fmt.hash(e.after_sha256, 8))))))) : null,
            editForm(p)),
        section('Kiểm định và thẩm định', null,
            h('div', { class: 'grid cols-2' },
                h('div', { class: 'panel stack' }, h('h3', {}, 'Cổng chất lượng'),
                    h('div', { class: 'row' }, decisionChip(q.G2_pattern?.decision, 'G2 hoa văn: '), decisionChip(q.G3_final?.decision, 'G3 áo: '),
                        q.repair ? decisionChip(q.repair.overall?.decision, 'Bản sửa: ') : null),
                    h('p', { class: 'small' }, q.overall?.message || ''), h('p', { class: 'muted small' }, `Cấu hình ${q.config_version || '—'}, đo ${fmt.date(q.evaluated_at)}`)),
                h('div', { class: 'panel stack' }, h('h3', {}, 'Phiếu chuyên gia'),
                    p.reviews.length ? p.reviews.map((r) => h('div', { class: 'small' }, h('b', {}, `${r.reviewer_id} (${r.reviewer_role})`), `: ${r.decision}. `, r.comment,
                        r.rule_conflict ? h('span', { class: 'chip warn' }, 'Mâu thuẫn quy tắc') : null))
                        : h('p', { class: 'muted' }, 'Chưa có phiếu nào. Thiết kế chưa được phê duyệt.')))),
        section('Phạm vi sử dụng', 'Do Cổng quyền sử dụng quyết định theo tình trạng giấy phép của ảnh hiện vật.',
            h('div', { class: 'table-wrap' }, h('table', { class: 'data' }, h('tbody', {}, Object.entries(p.rights || {}).map(([a, gte]) => h('tr', {},
                h('td', {}, ACTION[a] || a), h('td', {}, decisionChip(gte.level === 'ok' ? 'PASS' : gte.level === 'warn' ? 'WARN' : 'FAIL')), h('td', { class: 'small' }, gte.reason))))))),
        section('Dòng thời gian', 'Mỗi sự kiện chứa mã băm của sự kiện trước; sửa lén một dòng sẽ làm kiểm tra toàn vẹn báo lỗi.',
            h('ol', { class: 'timeline' }, (p.timeline || []).map((t) => h('li', {}, actorMark(t.actor_type),
                h('div', { class: 'when' }, t.at ? fmt.date(t.at) : 'Không ghi nhận thời điểm'),
                h('div', { class: 'what' }, eventLabel(t)),
                h('div', { class: 'hash' }, `${t.actor}, khối ${t.entry_hash}`))))));
}

export async function render([pid]) {
    if (pid) return detail(pid);
    const passports = await data.passports();
    if (!passports.length) return stateBox('', 'Chưa có Design Passport', 'Sinh thiết kế trong Studio để tạo hồ sơ đầu tiên.', h('a', { class: 'btn primary', href: '#/studio' }, 'Mở Studio'));
    return list(passports);
}
