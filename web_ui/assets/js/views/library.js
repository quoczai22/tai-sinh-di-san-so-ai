// views/library.js — TRANG CHỦ (#/library) dành cho người xem: chỉ ảnh, tên và câu chuyện, theo 5 phần cuộn:
//  1. Lời mở (chữ sáng dần)  2. Hành trình (khối dính, thẻ trượt ngang)  3. Bộ sưu tập hiện vật (bấm → Studio)
//  4. Tà áo (lưới áo dài, chỉ để xem)  5. Đích đến (mặt trống đồng + nút Bắt đầu thiết kế).
// View chỉ lấy dữ liệu và ghép component / hình trang trí; không tự định nghĩa component.
import { h } from '../core/dom.js';
import { icon } from '../core/icons.js';
import * as data from '../core/data.js';
import { byPref, latestOf } from '../core/designs.js';
import { litWords } from '../core/reveal.js';
import { artifactCard } from '../components/artifact-card.js';
import { chapterHead } from '../components/chapter-head.js';
import { galleryItem } from '../components/gallery-item.js';
import { journeyCard } from '../components/journey-card.js';
import { cloud, drum, thread } from '../decor/drum.js';
import { phoenix } from '../decor/phoenix.js';

export async function render() {
    const { items } = await data.heritage();
    const passports = (await data.passports().catch(() => [])).filter((d) => d.thumb && d.approval.status !== 'qa_failed');
    const active = items.filter((i) => i.status === 'active');

    // ---- 1. Lời mở: câu văn sáng dần theo nhịp cuộn ----
    const statement = h('section', { class: 'statement', 'data-scene': '' },
        litWords(h('p', { class: 'statement-text' }),
            'Mỗi chiếc bình gốm Bát Tràng giữ một câu chuyện trong nét vẽ. Chúng tôi lần theo nét vẽ ấy, để nó sống tiếp trên tà áo dài.'));

    // ---- 2. Hành trình: khối dính, cuộn dọc thì các chặng trượt ngang ----
    const sample = [...passports].sort(byPref)[0];
    const sampleItem = sample ? items.find((i) => i.id === sample.heritage_id) : active[0];
    const dir = sample ? sample.thumb.replace(/final_img2img\.webp$/, '') : '';
    // Ba chặng người xem nhìn thấy được: hiện vật → hoa văn → tà áo
    const journey = [
        { title: 'Hiện vật', sub: 'Một chiếc bình gốm Bát Tràng có nguồn gốc rõ ràng.', img: sampleItem?.image, ai: false, contain: true },
        { title: 'Hoa văn', sub: 'Nét vẽ trên men được dệt thành tấm hoa văn liền mạch.', img: dir && `./${dir}pattern.webp`, ai: true },
        { title: 'Tà áo dài', sub: 'Hoa văn khoác lên dáng áo dài, giữ trọn nét gốc.', img: sample && `./${latestOf(sample)}`, ai: true },
    ];
    const journeySection = h('section', { class: 'journey-pin', 'data-pin': '' },
        h('div', { class: 'pin-sticky' },
            h('div', { class: 'pin-head' },
                h('p', { class: 'kicker' }, 'Hành trình'),
                h('h2', { class: 'display' }, 'Từ men gốm tới tà áo')),
            h('div', { class: 'pin-track', 'data-pin-track': '' }, journey.map((j, index) => journeyCard({ ...j, index }))),
            h('div', { class: 'pin-progress', 'aria-hidden': 'true' }, h('span'))));

    // ---- 3. Hiện vật: lưới ảnh, bình nổi lên theo nhịp cuộn ----
    const collection = h('section', { class: 'section chapter', id: 'hien-vat', tabindex: '-1' },
        chapterHead('Bộ sưu tập', 'Hiện vật', 'Những chiếc bình gốm làm nguồn hoa văn.'),
        h('div', { class: 'artifact-grid-v2' }, active.map(artifactCard)));

    // ---- 4. Tà áo: mỗi hiện vật một tà áo tiêu biểu, chia ba cột ----
    const picks = [];
    for (const it of active) picks.push(...passports.filter((d) => d.heritage_id === it.id).sort(byPref).slice(0, 1));
    const nameOf = Object.fromEntries(items.map((i) => [i.id, i.name]));
    const cols = [[], [], []];
    picks.forEach((d, i) => cols[i % 3].push(galleryItem(d, nameOf[d.heritage_id])));
    const gallery = picks.length ? h('section', { class: 'section chapter gallery', 'data-scene': '' },
        chapterHead('Tà áo', 'Áo dài từ hoa văn gốm', null),
        h('div', { class: 'gallery-cols' }, cols.map((c, i) => h('div', { class: 'gallery-col', style: { '--s': String([1, -1.4, 0.7][i]) } }, c)))) : null;

    // ---- 5. Đích đến: mặt trống đồng — nơi con đường hội tụ ----
    const finale = h('section', { class: 'finale', 'data-scene': '' },
        h('div', { class: 'finale-inner' },
            h('div', { class: 'finale-drum' }, drum()),
            h('div', { class: 'finale-copy' },
                cloud('finale-cloud'),
                h('h2', { class: 'display' }, 'Di sản được khoác lên người'),
                h('div', { class: 'finale-ctas' }, h('a', { class: 'btn hero-btn primary', href: '#/studio' }, 'Bắt đầu thiết kế', icon('arrow'))))));

    return h('div', { class: 'exhibit home' }, phoenix(), statement, journeySection, thread(), collection, thread(), gallery, thread(), finale);
}
