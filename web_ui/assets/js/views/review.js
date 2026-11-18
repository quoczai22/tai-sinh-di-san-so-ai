import { downloadJson, fmt, h, toast } from '../lib/dom.js';
import * as data from '../lib/data.js';
import { approvalChip, section, stateBox } from '../lib/ui.js';

const QUEUES = [
    ['expert', 'Chờ chuyên gia', (p) => ['pending_expert_review', 'revision_requested'].includes(p.approval.status)],
    ['qc', 'Chờ QC xem cảnh báo', (p) => p.approval.status === 'qa_warning'],
    ['done', 'Đã có quyết định', (p) => ['approved', 'rejected'].includes(p.approval.status)],
];

// Chế độ chấm mù dùng chung cho hàng đợi và phiếu. Khi bật: không hiện mã Passport
// (mã chứa số biến thể V1–V4, tương ứng trọng số ControlNet), xếp hàng đợi theo mã ẩn danh.
const blindState = { on: true, listeners: new Set() };
function setBlind(on) { blindState.on = on; blindState.listeners.forEach((fn) => fn()); }
function anonCode(id) {
    let x = 2166136261;
    for (const ch of id) { x ^= ch.charCodeAt(0); x = Math.imul(x, 16777619) >>> 0; }
    return `T${String(1000 + (x % 9000))}`;
}

function scaleControl(crit, scores, scale) {
    const group = h('div', { class: 'scale', role: 'radiogroup', 'aria-label': crit.label });
    for (let v = scale.min; v <= scale.max; v += 1) {
        group.append(h('button', { type: 'button', role: 'radio', 'aria-pressed': 'false', 'aria-checked': 'false',
            title: scale.labels[String(v)], onclick: (e) => {
                scores[crit.key] = v;
                [...group.children].forEach((b) => { const on = b === e.currentTarget; b.setAttribute('aria-pressed', String(on)); b.setAttribute('aria-checked', String(on)); });
            } }, String(v)));
    }
    return h('div', { class: 'score' }, h('b', {}, crit.label), group, h('div', { class: 'q' }, crit.question));
}

async function expertForm(p, rubric, onDone) {
    const scores = {};
    const blindToggle = h('input', { type: 'checkbox', checked: blindState.on, id: 'blind' });
    const versions = p.versions.map((v) => ({ v: v.version, label: v.kind === 'system_repair' ? 'Bản khoá họa tiết' : v.kind === 'human_edit' ? 'Bản chỉnh sửa thủ công' : 'Bản img2img', art: p.artifacts.find((a) => a.path === v.path) }));
    // Đánh giá mù: xáo thứ tự phương án theo mã người chấm, ẩn tên phương án
    const order = versions.slice();
    const ref = p.artifacts.find((a) => a.role === 'reference_512');
    const gallery = h('div', { class: 'grid cols-2' });
    const drawGallery = () => {
        const blind = blindToggle.checked;
        const seq = blind ? order.slice().sort((a, b) => ((a.v * 7919) % 13) - ((b.v * 7919) % 13)) : order;
        gallery.replaceChildren(
            h('figure', { style: { margin: 0 } }, h('img', { src: data.media(ref, ref?.display), alt: 'Hiện vật gốc', style: { background: '#fff', borderRadius: '10px', border: '1px solid var(--line)' } }), h('figcaption', { class: 'small muted' }, `Hiện vật gốc: ${p.heritage.name}`)),
            ...seq.map((x, i) => h('figure', { style: { margin: 0 } },
                h('img', { src: data.media(x.art, x.art?.display), alt: blind ? `Phương án ${String.fromCharCode(65 + i)}` : x.label, style: { borderRadius: '10px', border: '1px solid var(--line)' } }),
                h('figcaption', { class: 'small muted' }, blind ? `Phương án ${String.fromCharCode(65 + i)}` : `${x.label} (v${x.v})`))));
        versionSel.replaceChildren(...seq.map((x, i) => h('option', { value: x.v }, blind ? `Phương án ${String.fromCharCode(65 + i)}` : `${x.label} (v${x.v})`)));
    };
    const versionSel = h('select', {});
    blindToggle.addEventListener('change', () => { setBlind(blindToggle.checked); drawGallery(); });
    drawGallery();

    const reviewerId = h('input', { placeholder: 'Ví dụ: CG01', maxlength: 24, pattern: '[A-Za-z0-9_-]+', required: true });
    const role = h('select', {}, h('option', { value: 'heritage_expert' }, 'Chuyên gia di sản'), h('option', { value: 'design_expert' }, 'Chuyên gia thiết kế'));
    const consent = h('input', { type: 'checkbox' });
    const nameInput = h('input', { maxlength: 80, disabled: true, placeholder: 'Chỉ lưu khi đồng ý' });
    consent.addEventListener('change', () => { nameInput.disabled = !consent.checked; });
    const decision = h('select', {}, h('option', { value: 'approve' }, 'Đạt, phê duyệt'), h('option', { value: 'revise' }, 'Cần chỉnh sửa'), h('option', { value: 'reject' }, 'Loại'));
    const comment = h('textarea', { maxlength: 2000, placeholder: 'Bắt buộc khi yêu cầu sửa hoặc loại: ghi rõ lý do và bước cần làm lại.' });
    const warn = h('p', { class: 'note warn', hidden: true });

    const collect = () => {
        const id = reviewerId.value.trim();
        if (!/^[A-Za-z0-9_-]{2,24}$/.test(id)) throw new Error('Nhập mã người chấm (2–24 ký tự, chữ, số, gạch).');
        const missing = rubric.criteria.filter((c) => !scores[c.key]);
        if (missing.length) throw new Error(`Chưa chấm: ${missing.map((c) => c.label).join(', ')}.`);
        if (decision.value !== 'approve' && comment.value.trim().length < 5) throw new Error('Ghi lý do khi yêu cầu sửa hoặc loại.');
        return { reviewer_id: id, reviewer_role: role.value, consent_to_store_name: consent.checked,
            reviewer_name: consent.checked ? nameInput.value.trim() || null : null, blind: blindToggle.checked,
            scores: { ...scores }, decision: decision.value, comment: comment.value.trim(), reviewed_version: Number(versionSel.value) };
    };
    const ruleCheck = (r) => {
        const low = Object.entries(r.scores).filter(([, v]) => v < 3).map(([k]) => rubric.criteria.find((c) => c.key === k)?.label);
        const culture = r.scores.cultural_appropriateness;
        if (r.decision === 'approve' && (low.length || culture < 4)) {
            warn.hidden = false;
            warn.textContent = `Quyết định "Đạt" mâu thuẫn với quy tắc của bộ tiêu chí (${low.length ? `điểm dưới 3: ${low.join(', ')}` : 'phù hợp văn hoá dưới 4'}). Phiếu vẫn được ghi nhưng đánh dấu mâu thuẫn để hội đồng xem lại.`;
        } else warn.hidden = true;
    };

    const submit = h('button', { class: 'btn primary', type: 'button', onclick: async () => {
        try {
            const review = collect();
            ruleCheck(review);
            if (data.isLive()) {
                await data.submitReview(p.passport_id, review);
                toast('Đã ghi phiếu thẩm định vào Design Passport.');
                onDone();
            } else {
                downloadJson(`phieu_${p.passport_id}_${review.reviewer_id}.json`, { passport_id: p.passport_id, rubric_version: rubric.version, ...review });
                toast('Đã xuất phiếu. Gửi tệp cho nhóm để nhập vào hệ thống.');
            }
        } catch (err) { toast(err.message); }
    } }, data.isLive() ? 'Ghi phiếu thẩm định' : 'Xuất phiếu thẩm định (.json)');

    return h('div', { class: 'review-layout' },
        h('div', { class: 'stack' },
            h('label', { class: 'row small' }, blindToggle, 'Chấm mù: ẩn mã thiết kế, tham số và điểm AI'),
            gallery,
            h('p', { class: 'muted small' }, 'Không xem điểm kiểm định tự động khi đang chấm mù, để tránh bị neo theo con số máy đo.')),
        h('form', { class: 'panel stack', onsubmit: (e) => e.preventDefault() },
            h('h3', {}, 'Phiếu thẩm định'),
            h('div', { class: 'grid cols-2' }, h('label', { class: 'field' }, 'Mã người chấm', reviewerId), h('label', { class: 'field' }, 'Vai trò', role)),
            h('label', { class: 'row small' }, consent, 'Đồng ý lưu họ tên vào hồ sơ (không bắt buộc)'),
            h('label', { class: 'field' }, 'Họ tên', nameInput),
            h('label', { class: 'field' }, 'Phương án được chấm', versionSel),
            rubric.criteria.map((c) => scaleControl(c, scores, rubric.scale)),
            h('label', { class: 'field' }, 'Quyết định', decision),
            h('label', { class: 'field' }, 'Nhận xét', comment),
            warn,
            data.isLive() ? null : h('p', { class: 'note' }, 'Chưa kết nối máy chủ — phiếu được xuất thành tệp, chưa ghi vào hồ sơ chính thức.'),
            submit));
}

function qcForm(p, onDone) {
    const officer = h('input', { placeholder: 'Ví dụ: QC01', maxlength: 24 });
    const note = h('textarea', { maxlength: 1000, placeholder: 'Ghi chú cho chuyên gia hoặc cho nhóm sửa' });
    const q = p.quality || {};
    const warns = [...Object.values(q.G2_pattern?.metrics || {}), ...Object.values(q.G3_final?.metrics || {}), ...Object.values(q.repair?.G3_final?.metrics || {})]
        .filter((m) => m.status === 'WARN');
    const act = (decision) => async () => {
        const body = { officer_id: officer.value.trim(), decision, note: note.value.trim() };
        if (!/^[A-Za-z0-9_-]{2,24}$/.test(body.officer_id)) { toast('Nhập mã QC.'); return; }
        if (!data.isLive()) { downloadJson(`qc_${p.passport_id}.json`, { passport_id: p.passport_id, ...body }); toast('Đã xuất quyết định QC.'); return; }
        try { await data.submitQc(p.passport_id, body); toast('Đã ghi quyết định QC.'); onDone(); } catch (err) { toast(err.message); }
    };
    const fin = p.artifacts.find((a) => a.role === 'repair_pattern_lock') || p.artifacts.find((a) => a.role === 'final_img2img');
    return h('div', { class: 'review-layout' },
        h('img', { src: data.media(fin, fin?.display), alt: 'Thiết kế', style: { borderRadius: '12px', border: '1px solid var(--line)' } }),
        h('div', { class: 'panel stack' },
            h('h3', {}, 'Cảnh báo cần QC xem'),
            warns.length ? warns.map((m) => h('p', { class: 'note warn' }, `${m.label}: ${fmt.num(m.value, 3)} (ngưỡng cảnh báo ${fmt.num(m.warn, 2)})`)) : h('p', {}, 'Không có.'),
            h('label', { class: 'field' }, 'Mã QC', officer),
            h('label', { class: 'field' }, 'Ghi chú', note),
            h('div', { class: 'row' }, h('button', { class: 'btn primary', type: 'button', onclick: act('forward_to_expert') }, 'Chuyển chuyên gia'),
                h('button', { class: 'btn', type: 'button', onclick: act('return_for_repair') }, 'Trả về để sửa'))));
}

export async function render([pid]) {
    const [list, rubric] = await Promise.all([data.passports(), fetch('./data/rubric.json').then((r) => r.json())]);
    let tab = 'expert';
    let current = pid || null;
    const queueEl = h('div', { class: 'stack' });
    const detail = h('div', {});
    const drawQueue = () => {
        const [, , fn] = QUEUES.find((q) => q[0] === tab);
        const blind = blindState.on && tab === 'expert';
        const items = list.filter(fn);
        if (blind) items.sort((a, b) => anonCode(a.passport_id).localeCompare(anonCode(b.passport_id)));
        queueEl.replaceChildren(...(items.length ? items.map((p) => h('button', { class: 'queue-item', 'aria-current': String(p.passport_id === current),
            onclick: () => { current = p.passport_id; drawQueue(); drawDetail(); } },
        h('img', { src: data.media(p.final_path, p.thumb), alt: '' }),
        h('div', {}, h('div', { style: { fontWeight: 600 } }, p.heritage_name),
            h('div', { class: 'small muted' }, blind ? `Thiết kế ${anonCode(p.passport_id)}` : p.passport_id),
            // Trạng thái chỉ hiện khi khác trạng thái chung của hàng đợi
            ['pending_expert_review', 'qa_warning'].includes(p.approval.status) ? null : approvalChip(p.approval.status)))) :
            [h('p', { class: 'muted' }, 'Không có thiết kế nào trong hàng đợi này.')]));
    };
    let renderHeader = () => {};
    const sortedQueue = (fn) => {
        const items = list.filter(fn);
        return blindState.on && fn === QUEUES[0][2]
            ? items.sort((a, b) => anonCode(a.passport_id).localeCompare(anonCode(b.passport_id))) : items;
    };
    const drawDetail = async () => {
        if (!current) { detail.replaceChildren(stateBox('', 'Chọn một thiết kế trong hàng đợi', null)); return; }
        detail.replaceChildren(h('div', { class: 'skeleton' }));
        const p = await data.passport(current);
        data.audit('review_form_opened', { step: 5, passport_id: current });
        const refresh = async () => { data.invalidate('live:passports'); location.hash = `#/review/${current}`; window.dispatchEvent(new HashChangeEvent('hashchange')); };
        const status = p.approval.status;
        let body;
        if (status === 'qa_warning') body = qcForm(p, refresh);
        else if (['pending_expert_review', 'revision_requested'].includes(status)) body = await expertForm(p, rubric, refresh);
        else body = h('div', { class: 'stack' }, h('p', {}, 'Thiết kế này không ở trạng thái chờ thẩm định.'), approvalChip(status),
            p.reviews.map((r) => h('div', { class: 'panel small' }, `${r.reviewer_id} (${r.reviewer_role}): ${r.decision}. ${r.comment}`)));
        const header = h('div', { class: 'row spread', style: { marginBottom: '12px' } });
        renderHeader = () => {
            const hideId = blindState.on && ['pending_expert_review', 'revision_requested'].includes(status);
            header.replaceChildren(hideId ? h('span', { class: 'small muted' }, `Thiết kế ${anonCode(p.passport_id)} (mã thật được ẩn khi chấm mù)`)
                : h('a', { href: `#/passport/${p.passport_id}` }, p.passport_id), approvalChip(status));
        };
        renderHeader();
        detail.replaceChildren(header, body);
    };
    const tabs = h('div', { class: 'tabs', role: 'group', 'aria-label': 'Hàng đợi' }, QUEUES.map(([key, label, fn]) =>
        h('button', { 'aria-pressed': String(key === tab), onclick: (e) => {
            tab = key;
            [...e.currentTarget.parentElement.children].forEach((b) => b.setAttribute('aria-pressed', String(b === e.currentTarget)));
            current = sortedQueue(fn)[0]?.passport_id;
            drawQueue(); drawDetail();
        } }, `${label} (${list.filter(fn).length})`)));
    if (pid) {
        const p = list.find((x) => x.passport_id === pid);
        tab = QUEUES.find(([, , fn]) => p && fn(p))?.[0] || 'expert';
    }
    if (!current) current = sortedQueue(QUEUES.find((q) => q[0] === tab)[2])[0]?.passport_id;
    blindState.listeners.clear();
    blindState.listeners.add(() => { drawQueue(); renderHeader(); });
    drawQueue();
    drawDetail();
    return h('div', {},
        section('Hàng đợi', 'Thiết kế có cảnh báo phải qua QC trước. Thiết kế không đạt kiểm định không vào hàng đợi chuyên gia.',
            h('div', { style: { marginBottom: '12px' } }, tabs),
            h('div', { class: 'queue-layout' },
                h('div', { class: 'panel', style: { maxHeight: '70vh', overflowY: 'auto', padding: '8px' } }, queueEl), detail)),
        section('Bộ tiêu chí', `${rubric.version}. ${rubric.pass_rule}`,
            h('div', { class: 'grid cols-3' }, rubric.criteria.map((c) => h('div', { class: 'panel' }, h('h3', {}, c.label), h('p', { class: 'small' }, c.question),
                h('p', { class: 'muted small' }, c.owner === 'heritage' ? 'Chuyên gia di sản chấm' : 'Chuyên gia thiết kế chấm'))))));
}
