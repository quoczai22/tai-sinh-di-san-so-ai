// views/mine.js — TRANG THIẾT KẾ ĐÃ TẠO (#/mine): danh sách các bộ thiết kế đã tạo trên trình duyệt này, mở lại không cần tạo lại.
// Danh sách tên bộ lưu trong trình duyệt (core/data.myRuns); ảnh và hồ sơ vẫn nằm trên máy chủ nên chỉ mở lại được khi máy chủ còn bộ đó.
// Không đồng bộ giữa thiết bị. View chỉ lấy dữ liệu và ghép component; không tự định nghĩa component.
import { h } from '../core/dom.js';
import * as data from '../core/data.js';
import { stateBox } from '../components/layout.js';
import { runCard } from '../components/run-card.js';

export async function render() {
    data.enterLive();
    const runs = data.myRuns();
    if (!runs.length) {
        return stateBox('', 'Bạn chưa tạo thiết kế nào', 'Các bộ thiết kế bạn tạo ở Studio sẽ xuất hiện ở đây.',
            h('a', { class: 'btn primary', href: '#/studio' }, 'Vào Studio'));
    }
    const [{ items }, list] = await Promise.all([data.heritage(), data.passports()]);
    if (!data.isLive()) {
        return stateBox('error', 'Chưa kết nối được máy chủ', 'Không lấy được các bộ thiết kế đã tạo. Hãy thử lại sau ít phút.',
            h('button', { class: 'btn', type: 'button', onclick: () => location.reload() }, 'Tải lại'));
    }
    const cards = runs.map((run) => runCard({
        run, item: items.find((i) => i.id === run.heritageId),
        designs: list.filter((p) => p.run_id === run.runId && (p.thumb || p.final_path)).sort((a, b) => a.passport_id.localeCompare(b.passport_id)),
    }));
    return h('div', { class: 'mine' }, h('div', { class: 'mine-grid' }, cards));
}
