// views/edit.js — TRANG TẢI BẢN CHỈNH SỬA (#/edit/<mã Passport>): chỉ dành cho thiết kế tạo trực tiếp trên máy chủ (có Passport ở đó).
// Thiết kế sinh sẵn của chế độ trình diễn không có hồ sơ trên máy chủ nên không chỉnh sửa được, trang nói rõ lý do.
// View chỉ lấy dữ liệu và ghép component; không tự định nghĩa component.
import { h } from '../core/dom.js';
import * as data from '../core/data.js';
import { latestOf, shownPath } from '../core/designs.js';
import { stateBox } from '../components/layout.js';
import { editPanel } from '../components/edit-panel.js';

export async function render([passportId]) {
    data.enterLive();
    const [{ items }, list] = await Promise.all([data.heritage(), data.passports()]);
    const design = data.isLive() ? list.find((p) => p.passport_id === passportId) : null;
    if (!design) {
        return stateBox('error', 'Không mở được trang chỉnh sửa',
            'Chỉ thiết kế bạn tạo trực tiếp ở Studio (và còn trên máy chủ) mới chỉnh sửa được. Thiết kế sinh sẵn của bản trình diễn thì không.',
            h('a', { class: 'btn', href: '#/mine' }, 'Về Thiết kế đã tạo'));
    }
    const siblings = list.filter((p) => p.run_id === design.run_id).sort((a, b) => a.passport_id.localeCompare(b.passport_id));
    const item = items.find((i) => i.id === design.heritage_id);
    return editPanel({
        design, n: siblings.findIndex((p) => p.passport_id === design.passport_id) + 1,
        heritageName: item?.name || design.heritage_name || design.heritage_id,
        imageSrc: data.media(shownPath(design), latestOf(design)),
        resultHref: `#/result/${encodeURIComponent(design.heritage_id)}/${encodeURIComponent(design.run_id)}`,
    });
}
