import { fmt, h } from '../lib/dom.js';
import * as data from '../lib/data.js';
import { statusBar } from '../lib/charts.js';
import { APPROVAL, section, stat } from '../lib/ui.js';

const count = (arr, fn) => arr.reduce((acc, x) => { const k = fn(x); if (k) acc[k] = (acc[k] || 0) + 1; return acc; }, {});

export async function render() {
    const [{ items }, passports, exps, snap] = await Promise.all([data.heritage(), data.passports(), data.experiments(),
        data.dashboardSnapshot().catch(() => null)]);
    const active = items.filter((i) => i.status === 'active');
    const clearRights = active.filter((i) => ['public_domain', 'open_license', 'permission_granted', 'own_work'].includes(i.provenance?.rightsStatus)).length;
    const completeness = active.length ? active.reduce((s, i) => s + i.completeness.ratio, 0) / active.length : 0;
    const n = passports.length;
    const g2 = count(passports, (p) => p.g2);
    const g3 = count(passports, (p) => p.g3);
    const approvals = count(passports, (p) => p.approval.status);
    const reviews = passports.reduce((s, p) => s + p.reviews, 0);
    const edits = passports.reduce((s, p) => s + p.edits, 0);
    const approved = approvals.approved || 0;
    const decided = approved + (approvals.rejected || 0);
    const planned = exps.reduce((s, e) => s + e.planned_runs, 0);
    const done = exps.reduce((s, e) => s + e.completed_runs, 0);

    const repaired = passports.filter((p) => p.repair_decision);
    const repairedOk = repaired.filter((p) => p.repair_decision !== 'FAIL').length;
    const integ = snap?.designs?.integrity;
    const dur = snap?.generation_duration_s;
    // Mã KPI khớp docs/finals/08_KPI.md
    const kpis = [
        ['K09', 'Hồ sơ nguồn đầy đủ (hiện vật đang dùng)', fmt.pct(completeness), 'Đo', '10/10 trường cho mọi hiện vật đang dùng'],
        ['K10', 'Hiện vật đang dùng được phép xuất bản', `${clearRights}/${active.length}`, 'Đo', 'Tất cả, trước khi xuất bản công khai'],
        ['K04', 'Hoa văn không đạt G2 (rò dáng bình, đường nối)', `${g2.FAIL || 0}/${n}`, 'Đo', 'Đặt sau EXP-A'],
        ['K01', 'Thiết kế cuối qua G3 ngay lần đầu', `${g3.PASS || 0}/${n}`, 'Đo', 'Đặt sau EXP-B'],
        ['K02', 'Sửa tự động đưa G3 về không FAIL', repaired.length ? `${repairedOk}/${repaired.length}` : 'Chưa có ca sửa', repaired.length ? 'Đo' : 'Mục tiêu cần đo', '≥ 90% và chuyên gia không chấm bản sửa kém hơn'],
        ['K11', 'Passport qua kiểm tra toàn vẹn', integ ? `${integ.ok}/${integ.total}` : 'Xem từng Passport', integ ? 'Đo (lúc xuất dữ liệu)' : 'Mục tiêu cần đo', '100%'],
        ['K14', 'Tỉ lệ phê duyệt sau thẩm định', decided ? fmt.pct(approved / decided) : 'Chưa có phiếu', decided ? 'Đo' : 'Mục tiêu cần đo', 'Đặt sau khi có dữ liệu'],
        ['K06', 'Độ đồng thuận người chấm (Krippendorff alpha)', 'Chưa có phiếu', 'Mục tiêu cần đo', '≥ 0,667 trước khi kết luận'],
        ['K07', 'Dao động theo seed (hệ số biến thiên PPS)', 'Chưa chạy EXP-A', 'Mục tiêu cần đo', 'Báo cáo kèm mọi kết luận'],
        ['K12', 'Thời gian sinh một biến thể (trung vị)', dur?.median ? `${fmt.num(dur.median, 2)} giây` : 'Chưa có', dur?.median ? 'Đo' : 'Mục tiêu cần đo', dur?.source || ''],
    ];
    return h('div', {},
        section('Hôm nay', `Số liệu tính từ ${data.isLive() ? 'API đang chạy' : 'dữ liệu đã xuất'}.`,
            h('div', { class: 'grid cols-4' },
                stat(`${active.length}`, 'Hiện vật đang dùng', `${items.length - active.length} hiện vật ngừng dùng theo tiêu chí tuyển ảnh v2`),
                stat(`${n}`, 'Thiết kế có Design Passport', `${edits} chỉnh sửa thủ công, ${reviews} phiếu chuyên gia`),
                stat(`${approvals.pending_expert_review || 0}`, 'Đang chờ chuyên gia', `${approvals.qa_warning || 0} chờ QC, ${approvals.qa_failed || 0} phải sinh lại`),
                stat(`${done}/${planned}`, 'Lượt thí nghiệm đã chạy', 'EXP-A và EXP-B cần GPU', planned ? done / planned : 0))),
        section('Trạng thái thiết kế', null,
            h('div', { class: 'grid cols-2' },
                h('div', { class: 'panel' }, h('h3', {}, 'Cổng G2 hoa văn'), statusBar(g2, n || 1)),
                h('div', { class: 'panel' }, h('h3', {}, 'Cổng G3 thiết kế cuối'), statusBar(g3, n || 1))),
            h('div', { class: 'table-wrap', style: { marginTop: '14px' } }, h('table', { class: 'data' },
                h('thead', {}, h('tr', {}, h('th', {}, 'Trạng thái phê duyệt'), h('th', { class: 'num' }, 'Số thiết kế'))),
                h('tbody', {}, Object.entries(APPROVAL).map(([k, v]) => h('tr', {}, h('td', {}, v.text), h('td', { class: 'num' }, approvals[k] || 0))))))),
        section('Bảng KPI', 'Cột "Loại" cho biết số đã đo được hay mới là mục tiêu cần đo. Không có số nào được ước đoán.',
            h('div', { class: 'table-wrap' }, h('table', { class: 'data' },
                h('thead', {}, h('tr', {}, ['Mã', 'Chỉ số', 'Hiện tại', 'Loại', 'Mục tiêu'].map((t) => h('th', {}, t)))),
                h('tbody', {}, kpis.map(([code, k, v, type, target]) => h('tr', {}, h('td', { class: 'small' }, code), h('td', {}, k), h('td', {}, h('b', {}, v)),
                    h('td', {}, h('span', { class: `chip ${type.startsWith('Đo') ? 'info' : 'neutral'}` }, type)), h('td', { class: 'small' }, target))))))));
}
