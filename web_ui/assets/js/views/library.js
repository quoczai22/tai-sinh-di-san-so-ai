import { h, icon } from '../lib/dom.js';
import * as data from '../lib/data.js';
import { litWords } from '../lib/motion.js';
import { phoenix } from '../lib/phoenix.js';
import { cloud, drum, thread } from '../lib/drum.js';
import { aiMark } from '../lib/ui.js';

// Trang chủ dành cho người xem: chỉ ảnh, tên và câu chuyện. Bấm hiện vật thì sang Studio của hiện vật đó;
// bấm tà áo thì sang trang Kết quả của hiện vật tạo ra nó.
const PREF = ['pending_expert_review', 'qa_warning', 'revision_requested', 'approved', 'qa_failed'];
const latestOf = (d) => (d.latest_version_kind === 'system_repair' && d.repair_thumb ? d.repair_thumb : d.thumb);
const byPref = (a, b) => (PREF.indexOf(a.approval.status) - PREF.indexOf(b.approval.status)) || a.passport_id.localeCompare(b.passport_id);

function chapterHead(kicker, title, lede) {
    return h('div', { class: 'chapter-intro' },
        kicker ? h('p', { class: 'kicker' }, kicker) : null,
        h('h2', { class: 'display' }, title),
        lede ? h('p', { class: 'lede' }, lede) : null);
}

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
        ['Hiện vật', 'Một chiếc bình gốm Bát Tràng có nguồn gốc rõ ràng.', sampleItem ? `#/studio/${encodeURIComponent(sampleItem.id)}` : '#/studio', sampleItem?.image, false, true],
        ['Hoa văn', 'Nét vẽ trên men được dệt thành tấm hoa văn liền mạch.', sampleItem ? `#/studio/${encodeURIComponent(sampleItem.id)}` : '#/studio', dir && `./${dir}pattern.webp`, true],
        ['Tà áo dài', 'Hoa văn khoác lên dáng áo dài, giữ trọn nét gốc.', sampleItem ? `#/result/${encodeURIComponent(sampleItem.id)}` : '#/studio', sample && `./${latestOf(sample)}`, true],
    ];
    const journeyCards = journey.map(([title, sub, href, img, ai, contain], i) => h('a', { class: 'journey-card', href },
        h('div', { class: `jc-img ${contain ? 'contain' : ''}` }, img ? h('img', { src: img, alt: '', loading: 'lazy' }) : null),
        h('span', { class: 'jc-num' }, String(i + 1).padStart(2, '0')),
        ai ? aiMark() : null,
        h('div', { class: 'jc-body' }, h('h3', {}, title), h('p', {}, sub))));
    const journeySection = h('section', { class: 'journey-pin', 'data-pin': '' },
        h('div', { class: 'pin-sticky' },
            h('div', { class: 'pin-head' },
                h('p', { class: 'kicker' }, 'Hành trình'),
                h('h2', { class: 'display' }, 'Từ men gốm tới tà áo')),
            h('div', { class: 'pin-track', 'data-pin-track': '' }, journeyCards),
            h('div', { class: 'pin-progress', 'aria-hidden': 'true' }, h('span'))));

    // ---- 3. Hiện vật: lưới ảnh, bình nổi lên theo nhịp cuộn ----
    const artifactCard = (it, k) => h('a', { class: 'artifact-card', href: `#/studio/${encodeURIComponent(it.id)}`, 'data-scene': '', style: { '--k': String(k % 3) },
        'aria-label': `${it.name}, tạo thiết kế` },
    h('div', { class: 'ac-stage' }, h('div', { class: 'ac-halo', 'aria-hidden': 'true' }), h('img', { src: it.image, alt: '', loading: 'lazy' })),
    h('div', { class: 'ac-body' },
        h('div', { class: 'code' }, it.dating || 'Gốm Bát Tràng'),
        h('div', { class: 'name' }, it.name)));
    const collection = h('section', { class: 'section chapter', id: 'hien-vat', tabindex: '-1' },
        chapterHead('Bộ sưu tập', 'Hiện vật', 'Những chiếc bình gốm làm nguồn hoa văn.'),
        h('div', { class: 'artifact-grid-v2' }, active.map(artifactCard)));

    // ---- 4. Tà áo: ba cột trôi với tốc độ khác nhau ----
    const picks = [];
    for (const it of active) picks.push(...passports.filter((d) => d.heritage_id === it.id).sort(byPref).slice(0, 1));
    const nameOf = Object.fromEntries(items.map((i) => [i.id, i.name]));
    const designItem = (d) => h('a', { class: 'gallery-item', href: `#/result/${encodeURIComponent(d.heritage_id)}`, 'data-scene': '' },
        h('div', { class: 'gi-img' }, h('img', { src: `./${latestOf(d)}`, alt: `Áo dài hoa văn ${nameOf[d.heritage_id] || ''}`, loading: 'lazy' }), aiMark()));
    const cols = [[], [], []];
    picks.forEach((d, i) => cols[i % 3].push(designItem(d)));
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
