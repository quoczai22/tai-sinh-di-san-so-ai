const PUBLIC_BASE = 'https://tai-sinh-di-san-so-ai.vercel.app';

const VESSELS = [
    {
        num: 1,
        id: 'LR3D_33',
        code: 'HV07',
        name: 'Huy hiệu, mẫu đơn và dây sen',
        form: 'Hũ thân phình, vai rộng, cổ ngắn, hai quai đầu thú',
        motifText: 'Quanh vai là các ô vân như ý hình mây cụm chứa hoa lá, cùng dạng với hoa văn cổ áo mây trên vải vóc xưa. Thân bình phủ một băng mẫu đơn dây, loài hoa tượng trưng cho điềm may và vẻ đẹp nữ tính. Chân bình là hàng ô cánh sen, biểu tượng của sự thanh khiết trong Phật giáo.',
    },
    {
        num: 2,
        id: 'LR3D_61',
        code: 'HV08',
        name: 'Rồng và mây',
        form: 'Hũ thân tròn, vai đầy, cổ thẳng ngắn',
        motifText: 'Một con rồng thân dài phủ vảy uốn quanh bình giữa những dải mây xoắn. Rồng tượng trưng cho trời và hoàng đế, mây là điềm lành và hạnh phúc. Chân bình là hàng cánh sen dài, biểu tượng của sự thanh khiết trong Phật giáo.',
    },
    {
        num: 3,
        id: 'LR3D_50',
        code: 'HV09',
        name: 'Dây hoa cuộn dày',
        form: 'Bình cổ cao, thân cầu, miệng hơi loe',
        motifText: 'Dây hoa cuộn, chủ yếu là hoa sen, phủ kín cổ và thân bình; chân bình viền một hàng ô cánh sen nhỏ. Hoa sen gắn với Phật giáo, tượng trưng cho sự thanh khiết, đồng thời là biểu tượng của sự trường thọ và thanh nhã.',
    },
    {
        num: 4,
        id: 'LR3D_38',
        code: 'HV10',
        name: 'Cây hoa',
        form: 'Bình trụ cao, thân thon dài, vai xuôi',
        motifText: 'Những khóm cây hoa thân mảnh, hoa nhỏ kết chùm, vươn thẳng từ chân lên vai bình trên nền men xanh nhạt.',
    },
    {
        num: 5,
        id: 'LR3D_97',
        code: 'HV11',
        name: 'Nét lam thưa trên men kem',
        form: 'Bình dáng tỳ bà (ngọc hồ xuân): thân hình quả lê, cổ thắt, miệng loe',
        motifText: 'Dưới miệng bình là băng lá chuối, cổ vẽ mây xoắn, thân chia ô vẽ hoa lá cách điệu, chân là hàng cánh sen. Mây là điềm lành, sen tượng trưng cho sự thanh khiết. Cách chia băng này gần với những bình hoa lam Việt Nam thế kỷ 15.',
    },
    {
        num: 6,
        id: 'LR3D_124',
        code: 'HV12',
        name: 'Huy hiệu rồng',
        form: 'Bình vuông bốn mặt, cổ thẳng ngắn',
        motifText: 'Vai bình viền một băng vân như ý; giữa thân là ô tròn có con rồng cuộn mình, biểu tượng của trời và hoàng đế; chân bình là băng lá chuối.',
    },
];

function formatBookBlock(vessel) {
    return (
        `📖 Sổ hoa văn — Bình #${vessel.num}: ${vessel.name}\n` +
        `• Dáng bình: ${vessel.form}\n` +
        `• Hoa văn & ý nghĩa: ${vessel.motifText}\n` +
        '• Nguồn ảnh: Bộ dữ liệu LR3D-CULT2 (Nguyen và cộng sự, FPT University), Mendeley Data (DOI 10.17632/jr23fnrvx2.1) · Giấy phép CC BY 4.0.'
    );
}

const lastJobByChat = new Map();

function findVessel(query) {
    const q = String(query || '').trim().toUpperCase();
    const num = Number(q);
    if (Number.isInteger(num) && num >= 1 && num <= VESSELS.length) {
        return VESSELS[num - 1];
    }
    return VESSELS.find((v) => v.id === q || v.code === q || `LR3D_${q}` === v.id) || null;
}

async function sendText(fetchWithTimeout, zaloBase, zaloToken, chatId, text) {
    await fetchWithTimeout(`${zaloBase}/bot${zaloToken}/sendMessage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chat_id: chatId, text }),
    }, 5000).catch(() => {});
}

async function sendPhoto(fetchWithTimeout, zaloBase, zaloToken, chatId, photoUrl, caption) {
    await fetchWithTimeout(`${zaloBase}/bot${zaloToken}/sendPhoto`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chat_id: chatId, photo: photoUrl, caption }),
    }, 8000).catch(() => {});
}

async function sendFourDesigns(fetchWithTimeout, zaloBase, zaloToken, chatId, vessel, urls, prefixLabel) {
    for (let i = 0; i < urls.length; i++) {
        await sendPhoto(
            fetchWithTimeout,
            zaloBase,
            zaloToken,
            chatId,
            urls[i],
            `${prefixLabel} · Thiết kế ${i + 1}/4 — Bình #${vessel.num}: ${vessel.name}`
        );
    }
}

async function pollAndSendWhenDone({
    jobId,
    vessel,
    chatId,
    hop,
    zaloBase,
    zaloToken,
    fetchWithTimeout,
    getBackendConfig,
    buildBackendHeaders,
}) {
    const config = getBackendConfig();
    const startMs = Date.now();
    const maxSliceMs = 34000;
    while (Date.now() - startMs < maxSliceMs) {
        await new Promise((r) => setTimeout(r, 3000));
        try {
            const res = await fetchWithTimeout(
                `${config.modalUrl}/generate/${encodeURIComponent(jobId)}`,
                { headers: buildBackendHeaders('modal', config) },
                8000
            );
            if (!res.ok) continue;
            const job = await res.json();
            if (['queued', 'running'].includes(job.status)) continue;
            if (job.status === 'completed' && job.run_id) {
                await sendText(
                    fetchWithTimeout,
                    zaloBase,
                    zaloToken,
                    chatId,
                    `✅ Đã sinh xong 4/4 thiết kế mới trên GPU T4 cho Bình #${vessel.num}: ${vessel.name}! Đang gửi 4 ảnh vào Zalo...`
                );
                const urls = [1, 2, 3, 4].map((i) => `${PUBLIC_BASE}/api/live/media/run/${job.run_id}/V${i}_aodai.png`);
                await sendFourDesigns(fetchWithTimeout, zaloBase, zaloToken, chatId, vessel, urls, 'Ảnh mới sinh từ GPU');
                return { ok: true, mode: 'vessel_auto_completed', runId: job.run_id };
            }
            await sendText(fetchWithTimeout, zaloBase, zaloToken, chatId, `⚠️ Lượt sinh kết thúc với trạng thái: ${job.status}.`);
            return { ok: true, mode: 'vessel_auto_failed' };
        } catch (_) {}
    }

    if (hop < 4) {
        const secret = (process.env.ALERT_ZALO_WEBHOOK_SECRET || '').trim();
        await fetchWithTimeout(`${PUBLIC_BASE}/api/live/zalo-webhook`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...(secret ? { 'x-bot-api-secret-token': secret } : {}),
            },
            body: JSON.stringify({
                internal_poll: { jobId, heritageId: vessel.id, chatId, hop: hop + 1 },
            }),
        }, 2500).catch(() => {});
        return { ok: true, mode: 'vessel_poll_continued', hop: hop + 1 };
    }

    await sendText(
        fetchWithTimeout,
        zaloBase,
        zaloToken,
        chatId,
        `⏳ GPU đang hoàn thiện bước cuối cho Bình #${vessel.num}: ${vessel.name}. Bạn gõ "xem" để nhận 4 ảnh nhé!`
    );
    return { ok: true, mode: 'vessel_poll_timeout' };
}

async function tryHandleDesignCommand({
    body,
    text,
    normalizedText,
    chatId,
    chatType,
    zaloBase,
    zaloToken,
    fetchWithTimeout,
    getBackendConfig,
    buildBackendHeaders,
}) {
    if (body?.internal_poll) {
        const { jobId, heritageId, chatId: targetChatId, hop = 1 } = body.internal_poll;
        const vessel = findVessel(heritageId) || VESSELS[0];
        if (!jobId || !targetChatId) return { ok: true, ignored: true };
        return pollAndSendWhenDone({
            jobId,
            vessel,
            chatId: String(targetChatId),
            hop: Number(hop) || 1,
            zaloBase,
            zaloToken,
            fetchWithTimeout,
            getBackendConfig,
            buildBackendHeaders,
        });
    }

    if (chatType !== 'PRIVATE') return null;

    const clean = normalizedText.trim();

    // 1. Danh sách bình: "binh", "danh sach", "menu", "chon binh"
    if (/^(binh|danh sach( binh)?|chon binh|menu|test binh)$/.test(clean)) {
        const lines = VESSELS.map((v) => `${v.num}. ${v.name}`).join('\n');
        const msg = `🏺 Danh sách 6 bình gốm Bát Tràng:\n${lines}\n\n` +
            '👉 Gõ "bình 1" .. "bình 6" (hoặc số 1..6): Nhận ngay 4 ảnh áo dài mẫu của bình đó.\n' +
            '👉 Gõ "sinh 1" .. "sinh 6": Gọi GPU Modal T4 sinh mới 4 ảnh thật và tự động gửi vào Zalo khi xong!';
        await sendText(fetchWithTimeout, zaloBase, zaloToken, chatId, msg);
        return { ok: true, mode: 'vessel_list' };
    }

    // 2. Xem nhanh 4 ảnh áo dài của bình: "binh 1", "ao 1", "1", "lr3d_61"
    const pickMatch = clean.match(/^(?:binh|ao|xem binh|test)\s+([1-6]|lr3d_\d+|hv\d+)$/) ||
        clean.match(/^([1-6]|lr3d_\d+)$/);
    if (pickMatch) {
        const vessel = findVessel(pickMatch[1]);
        if (!vessel) return null;
        await sendText(
            fetchWithTimeout,
            zaloBase,
            zaloToken,
            chatId,
            `${formatBookBlock(vessel)}\n\nĐang gửi 4 thiết kế áo dài vào Zalo của bạn...`
        );
        const urls = [1, 2, 3, 4].map((i) => `${PUBLIC_BASE}/assets/images/variants/${vessel.id}_V${i}_aodai.png`);
        await sendFourDesigns(fetchWithTimeout, zaloBase, zaloToken, chatId, vessel, urls, 'Áo dài');
        return { ok: true, mode: 'vessel_preview', heritageId: vessel.id };
    }

    // 3. Sinh thật trên GPU Modal và tự động chờ gửi 4 ảnh khi xong: "sinh 1..6" hoặc "gpu 1..6"
    const genMatch = clean.match(/^(?:sinh|gpu|tao)\s+([1-6]|lr3d_\d+|hv\d+)$/);
    if (genMatch) {
        const ownerId = (process.env.ALERT_ZALO_USER_CHAT_ID || '').trim();
        if (ownerId && chatId !== ownerId) {
            return { ok: true, ignored: 'operator_only' };
        }
        const vessel = findVessel(genMatch[1]);
        if (!vessel) return null;
        const config = getBackendConfig();
        if (!config.modalUrl || !config.modalKey) {
            await sendText(fetchWithTimeout, zaloBase, zaloToken, chatId, '⚠️ Chưa cấu hình MODAL_URL hoặc MODAL_KEY.');
            return { ok: true, mode: 'vessel_generate_error' };
        }
        try {
            const upstream = await fetchWithTimeout(`${config.modalUrl}/generate`, {
                method: 'POST',
                headers: { ...buildBackendHeaders('modal', config), 'Content-Type': 'application/json' },
                body: JSON.stringify({ heritage_id: vessel.id }),
            }, config.modalTimeoutMs);
            if (!upstream.ok) {
                await sendText(
                    fetchWithTimeout,
                    zaloBase,
                    zaloToken,
                    chatId,
                    `⚠️ Không thể tạo lượt sinh trên Modal (HTTP ${upstream.status}).`
                );
                return { ok: true, mode: 'vessel_generate_error', status: upstream.status };
            }
            const job = await upstream.json();
            lastJobByChat.set(chatId, { jobId: job.job_id, vessel });
            await sendText(
                fetchWithTimeout,
                zaloBase,
                zaloToken,
                chatId,
                `${formatBookBlock(vessel)}\n\n` +
                '🎨 Đang sinh 4 thiết kế mới trên GPU T4.\n' +
                '⏳ Bot sẽ tự động gửi 4 ảnh PNG vừa sinh vào đây ngay khi GPU chạy xong (khoảng 60–90 giây)!'
            );
            return await pollAndSendWhenDone({
                jobId: job.job_id,
                vessel,
                chatId,
                hop: 1,
                zaloBase,
                zaloToken,
                fetchWithTimeout,
                getBackendConfig,
                buildBackendHeaders,
            });
        } catch (_) {
            await sendText(fetchWithTimeout, zaloBase, zaloToken, chatId, '⚠️ Modal GPU đang khởi động chậm hoặc lỗi kết nối. Bạn thử lại sau ít giây nhé.');
            return { ok: true, mode: 'vessel_generate_error' };
        }
    }

    // 4. Gõ "xem" (hoặc "xem 1..6"): lấy 4 ảnh mới sinh gần nhất trên Modal Volume mà không cần mã jobId
    const watchMatch = clean.match(/^xem(?:\s+([1-6]|lr3d_\d+)(?:\s+([a-z0-9_-]+))?)?$/);
    if (watchMatch) {
        const saved = lastJobByChat.get(chatId);
        const vessel = (watchMatch[1] ? findVessel(watchMatch[1]) : null) || saved?.vessel || VESSELS[0];
        const config = getBackendConfig();
        try {
            const res = await fetchWithTimeout(
                `${config.modalUrl}/passports`,
                { headers: buildBackendHeaders('modal', config) },
                config.modalTimeoutMs
            );
            if (res.ok) {
                const items = await res.json();
                const forVessel = Array.isArray(items)
                    ? items.filter((p) => p.heritage_id === vessel.id && p.run_id)
                    : [];
                if (forVessel.length > 0) {
                    const latestRunId = forVessel.map((p) => p.run_id).sort().pop();
                    await sendText(
                        fetchWithTimeout,
                        zaloBase,
                        zaloToken,
                        chatId,
                        `${formatBookBlock(vessel)}\n\n✅ Đang gửi 4 ảnh mới nhất từ GPU Modal...`
                    );
                    const urls = [1, 2, 3, 4].map((i) => `${PUBLIC_BASE}/api/live/media/run/${latestRunId}/V${i}_aodai.png`);
                    await sendFourDesigns(fetchWithTimeout, zaloBase, zaloToken, chatId, vessel, urls, 'Ảnh mới sinh từ GPU');
                    return { ok: true, mode: 'vessel_watch_completed', runId: latestRunId };
                }
            }
        } catch (_) {}
        await sendText(fetchWithTimeout, zaloBase, zaloToken, chatId, '⏳ Lượt sinh GPU đang chạy hoặc chưa hoàn tất. Bạn đợi thêm vài giây rồi gõ lại "xem" nhé!');
        return { ok: true, mode: 'vessel_watch_running' };
    }

    return null;
}

module.exports = { tryHandleDesignCommand, VESSELS, formatBookBlock };
