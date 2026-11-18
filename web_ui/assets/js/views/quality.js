import { fmt, h } from '../lib/dom.js';
import * as data from '../lib/data.js';
import { dumbbell, statusBar } from '../lib/charts.js';
import { approvalChip, decisionChip, section, stat } from '../lib/ui.js';
import { openDesign } from './studio.js';

const count = (rows, key) => rows.reduce((acc, r) => { if (r[key]) acc[r[key]] = (acc[r[key]] || 0) + 1; return acc; }, {});

export async function render() {
    const [{ rows, config }, passports] = await Promise.all([data.quality(), data.passports()]);
    const byPid = Object.fromEntries(passports.map((p) => [p.passport_id, p]));
    const n = rows.length;
    const g2 = count(rows, 'G2');
    const g3 = count(rows, 'G3');
    const repaired = rows.filter((r) => r.repair_G3);
    const g3r = count(repaired, 'repair_G3');
    const eligible = passports.filter((p) => p.approval.status === 'pending_expert_review').length;

    const chartRows = [...rows].sort((a, b) => Number(a.pattern_preservation) - Number(b.pattern_preservation)).map((r) => ({
        label: r.passport_id.replace('DP-', '').replace('-20260906', ''),
        a: Number(r.pattern_preservation), b: r.repair_pps === '' ? null : Number(r.repair_pps),
        note: r.repair_pps === '' ? 'không tạo bản sửa' : '',
    }));
    const g3cfg = config.gates.G3_final.metrics;
    const g2cfg = config.gates.G2_pattern.metrics;

    return h('div', {},
        section('Kết quả trên 24 thiết kế ngày 06/09/2026',
            'Đo lại bằng Cổng G2/G3 trên CPU ngày 18/11/2026, so bản ghép tất định với thiết kế cuối sau img2img.',
            h('div', { class: 'grid cols-4' },
                stat(`${g2.PASS || 0}`, 'Hoa văn đạt cổng G2', `${g2.FAIL || 0} không đạt vì hoa văn là ảnh nguyên chiếc bình; ${g2.WARN || 0} cảnh báo`, (g2.PASS || 0) / n),
                stat(`${g3.PASS || 0}`, 'Thiết kế cuối đạt cổng G3 sau img2img', `${g3.FAIL || 0} không đạt giữ họa tiết, ${g3.WARN || 0} cảnh báo`, (g3.PASS || 0) / n),
                stat(`${g3r.PASS || 0}`, `Đạt sau khi khoá họa tiết (trên ${repaired.length} bản sửa)`, `${g3r.WARN || 0} còn cảnh báo, cần QC xem`, repaired.length ? (g3r.PASS || 0) / repaired.length : 0),
                stat(`${eligible}`, 'Đủ điều kiện chuyển chuyên gia', 'Chưa thiết kế nào được phê duyệt: còn chờ phiếu chuyên gia', eligible / n))),
        section('Lượt img2img vẽ lại họa tiết',
            'Mỗi hàng là một thiết kế. PPS là hệ số tương quan nét vẽ và sắc độ giữa bản ghép và thiết kế cuối (đã căn hình). Dưới 0,4 nghĩa là dưới 16% phương sai nét vẽ còn lại.',
            h('div', { class: 'panel' }, dumbbell({
                rows: chartRows, domain: [0, 1], valueLabel: 'Điểm giữ họa tiết',
                thresholds: [{ value: g3cfg.pattern_preservation.fail, label: 'Ngưỡng không đạt 0,4' }, { value: g3cfg.pattern_preservation.warn, label: 'Ngưỡng đạt 0,6' }],
                seriesA: { name: 'Sau img2img (strength 0,40)', color: '#B8742A' },
                seriesB: { name: 'Sau khoá họa tiết', color: '#24508A' },
            })),
            h('p', { class: 'note' }, 'Đọc đúng biểu đồ: điểm của bản khoá họa tiết cao do cấu tạo, vì bước sửa chép lại dải nét của bản ghép. Nó chứng minh bản sửa giữ được họa tiết, không chứng minh bản sửa đẹp hơn. Việc chọn bản nào do chuyên gia quyết định qua đánh giá mù (thí nghiệm EXP-B).')),
        section('Phân bố quyết định của cổng', null,
            h('div', { class: 'grid cols-3' },
                h('div', { class: 'panel' }, h('h3', {}, 'G2 hoa văn (24)'), statusBar(g2, n)),
                h('div', { class: 'panel' }, h('h3', {}, 'G3 sau img2img (24)'), statusBar(g3, n)),
                h('div', { class: 'panel' }, h('h3', {}, `G3 sau khoá họa tiết (${repaired.length})`), statusBar(g3r, repaired.length || 1)))),
        section('Ngưỡng đang dùng', `${config.version}, trạng thái tạm thời. ${config.calibration_note}`,
            h('div', { class: 'table-wrap' }, h('table', { class: 'data' },
                h('thead', {}, h('tr', {}, h('th', {}, 'Cổng'), h('th', {}, 'Chỉ số'), h('th', { class: 'num' }, 'Cảnh báo'), h('th', { class: 'num' }, 'Không đạt'), h('th', {}, 'Vì sao chọn ngưỡng này'))),
                h('tbody', {}, [...Object.entries(g2cfg).map(([k, m]) => ['G2', k, m]), ...Object.entries(g3cfg).map(([k, m]) => ['G3', k, m])].map(([gate, , m]) =>
                    h('tr', {}, h('td', {}, gate), h('td', {}, m.label), h('td', { class: 'num' }, fmt.num(m.warn, 2)), h('td', { class: 'num' }, fmt.num(m.fail, 2)), h('td', { class: 'small' }, m.why)))))),
            h('div', { class: 'grid cols-3', style: { marginTop: '14px' } },
                h('div', { class: 'panel' }, h('h3', {}, 'Không đạt ở G2'), h('p', { class: 'small' }, config.gates.G2_pattern.on_fail.action)),
                h('div', { class: 'panel' }, h('h3', {}, 'Không đạt ở G3'), h('p', { class: 'small' }, config.gates.G3_final.routing.pattern_preservation.action)),
                h('div', { class: 'panel' }, h('h3', {}, 'Giới hạn đã biết'), h('p', { class: 'small' }, 'Chỉ số rò dáng vật chứa không bắt được dạng hoa văn là các mảnh ghép của thân bình (hiện vật HV06, V1 và V2). Vì vậy mọi thiết kế vẫn phải qua chuyên gia.')))),
        section('Chi tiết từng thiết kế', 'Bấm mã để xem chuỗi truy vết và bảng chỉ số đầy đủ.',
            h('div', { class: 'table-wrap' }, h('table', { class: 'data' },
                h('thead', {}, h('tr', {}, ['Passport', 'Hiện vật', 'Trọng số', 'Rò dáng bình', 'Giữ họa tiết', 'Sau sửa', 'Dáng áo', 'G2', 'G3', 'Trạng thái'].map((t, i) => h('th', { class: i >= 2 && i <= 6 ? 'num' : '' }, t)))),
                h('tbody', {}, rows.map((r) => h('tr', {},
                    h('td', {}, h('button', { class: 'link-btn', onclick: () => openDesign(r.passport_id) }, r.passport_id)),
                    h('td', {}, byPid[r.passport_id]?.heritage_name || r.heritage_id, r.heritage_status === 'retired' ? h('span', { class: 'muted small' }, ' (ngừng dùng)') : null),
                    h('td', { class: 'num' }, fmt.num(r.controlnet_weight, 2)),
                    h('td', { class: 'num' }, fmt.num(r.vessel_leakage, 2)),
                    h('td', { class: 'num' }, fmt.num(r.pattern_preservation, 2)),
                    h('td', { class: 'num' }, r.repair_pps === '' ? '—' : fmt.num(r.repair_pps, 2)),
                    h('td', { class: 'num' }, fmt.num(r.garment_shape_iou, 3)),
                    h('td', {}, decisionChip(r.G2)), h('td', {}, decisionChip(r.G3)),
                    h('td', {}, approvalChip(byPid[r.passport_id]?.approval.status)))))))));
}
