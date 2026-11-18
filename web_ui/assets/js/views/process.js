import { h, icon } from '../lib/dom.js';
import { section } from '../lib/ui.js';

// [tệp ảnh, tiêu đề, mô tả, tệp nguồn, bề rộng hiển thị mặc định (px) — null = vừa khung]
const DIAGRAMS = [
    ['bpmn_to_be.svg', 'BPMN 2.0 TO-BE: quy trình end-to-end',
        'Một pool tổ chức với 4 lane (Nhà thiết kế, Hệ thống AI, Kiểm soát chất lượng, Dữ liệu và Passport) và hai pool bên ngoài (Hội đồng chuyên gia, Chủ sở hữu ảnh). Giữa các pool chỉ có message flow. Sơ đồ rộng, kéo ngang để xem hết.',
        'tsds_to_be.bpmn', 2600],
    ['bpmn_as_is.svg', 'BPMN 2.0 AS-IS: luồng trước cải tiến (bản 09/2026)',
        'Luồng một nút bấm: không có cổng chất lượng, không có thẩm định, ảnh mới ghi đè ảnh cũ nên không truy vết được lần chạy.',
        'tsds_as_is.bpmn', null],
    ['use_case.svg', 'UML Use Case',
        'Ranh giới hệ thống là nền tảng web và API. Hệ thống xử lý AI (máy GPU) là tác nhân phụ bên ngoài ranh giới. Màu nền cho biết ca sử dụng đã chạy được, chạy một phần hay mới là kế hoạch.',
        'use_case.puml', null],
];

function figure(file, title, width) {
    const img = h('img', { src: `./data/diagrams/${file}`, alt: title, loading: 'lazy' });
    const box = h('div', { class: 'diagram' + (width ? ' diagram--wide' : '') }, img);
    if (width) img.style.width = `${width}px`;
    const tools = h('div', { class: 'diagram-tools' });
    if (width) {
        const fit = h('button', { class: 'btn small', type: 'button', 'aria-pressed': 'false' }, icon('maximize'), 'Thu vừa khung');
        fit.addEventListener('click', () => {
            const fitted = fit.getAttribute('aria-pressed') === 'true';
            img.style.width = fitted ? `${width}px` : '100%';
            fit.setAttribute('aria-pressed', String(!fitted));
            fit.lastChild.textContent = fitted ? 'Thu vừa khung' : 'Xem cỡ thật';
        });
        tools.append(fit);
    }
    tools.append(h('a', { class: 'btn small', href: `./data/diagrams/${file}`, target: '_blank', rel: 'noopener' }, icon('external'), 'Mở ảnh SVG'));
    return h('div', {}, tools, box);
}

export async function render() {
    return h('div', {}, DIAGRAMS.map(([file, title, lede, source, width]) => section(title, lede,
        figure(file, title, width),
        h('p', { class: 'small muted' }, icon('info'), ` Tệp nguồn mở được bằng công cụ BPMN/PlantUML: docs/finals/diagrams/${source}. Giải thích chi tiết trong docs/finals.`))));
}
