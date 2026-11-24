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
    try {
        const response = await fetchWithTimeout(`${zaloBase}/bot${zaloToken}/sendPhoto`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chat_id: chatId, photo: photoUrl, caption }),
        }, 8000);
        if (!response.ok) return false;
        const result = await response.json();
        return result.ok !== false && (result.error_code == null || result.error_code === 0);
    } catch (_) {
        return false;
    }
}

async function sendFourDesigns(fetchWithTimeout, zaloBase, zaloToken, chatId, vessel, urls, prefixLabel) {
    let sent = 0;
    for (let i = 0; i < urls.length; i++) {
        if (await sendPhoto(
            fetchWithTimeout,
            zaloBase,
            zaloToken,
            chatId,
            urls[i],
            `${prefixLabel} · Thiết kế ${i + 1}/4 — Bình #${vessel.num}: ${vessel.name}`
        )) sent++;
    }
    return sent;
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
                    `✅ GPU đã hoàn tất lượt ${jobId} cho Bình #${vessel.num}: ${vessel.name}. Đang gửi ảnh vào Zalo...`
                );
                const urls = [1, 2, 3, 4].map((i) => `${PUBLIC_BASE}/api/live/media/run/${job.run_id}/V${i}_aodai.png`);
                const sent = await sendFourDesigns(fetchWithTimeout, zaloBase, zaloToken, chatId, vessel, urls, 'Ảnh mới sinh từ GPU');
                await sendText(fetchWithTimeout, zaloBase, zaloToken, chatId,
                    sent === 4 ? '✅ Đã gửi đủ 4 ảnh.' : `⚠️ Chỉ gửi được ${sent}/4 ảnh. Gõ "xem ${jobId}" để thử nhận lại đúng lượt này.`);
                return { ok: true, mode: 'vessel_auto_completed', runId: job.run_id, sent };
            }
            await sendText(fetchWithTimeout, zaloBase, zaloToken, chatId, `⚠️ Lượt sinh kết thúc với trạng thái: ${job.status}.`);
            return { ok: true, mode: 'vessel_auto_failed' };
        } catch (_) {}
    }

    if (hop < 4) {
        const secret = (process.env.ALERT_ZALO_WEBHOOK_SECRET || '').trim();
        try {
            const continuation = await fetchWithTimeout(`${PUBLIC_BASE}/api/live/zalo-webhook`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(secret ? { 'x-bot-api-secret-token': secret } : {}),
                },
                body: JSON.stringify({
                    internal_poll: { jobId, heritageId: vessel.id, chatId, hop: hop + 1 },
                }),
            }, 2500);
            if (continuation.ok) return { ok: true, mode: 'vessel_poll_continued', hop: hop + 1 };
        } catch (_) {}
    }

    await sendText(
        fetchWithTimeout,
        zaloBase,
        zaloToken,
        chatId,
        `⏳ Chưa xác nhận được ảnh đã gửi cho Bình #${vessel.num}: ${vessel.name}. Gõ "xem ${jobId}" để kiểm tra và nhận đúng lượt sinh này.`
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
            '👉 Gõ số "1" .. "6" (hoặc "bình 1" .. "bình 6"): Mở Sổ hoa văn xem dáng bình & ý nghĩa hoa văn.\n' +
            '👉 Gõ "sinh 1" .. "sinh 6": Gọi GPU Modal T4 sinh mới 4 ảnh thiết kế áo dài và gửi vào Zalo khi xong!';
        await sendText(fetchWithTimeout, zaloBase, zaloToken, chatId, msg);
        return { ok: true, mode: 'vessel_list' };
    }

    // 2. Xem chi tiết Sổ hoa văn + ảnh chiếc bình gốm (KHÔNG gửi ảnh áo dài mẫu): "1..6", "binh 1..6", "so 1..6"
    const pickMatch = clean.match(/^(?:binh|so|chi tiet|xem binh|mo ta)\s+([1-6]|lr3d_\d+|hv\d+)$/) ||
        clean.match(/^([1-6]|lr3d_\d+)$/);
    if (pickMatch) {
        const vessel = findVessel(pickMatch[1]);
        if (!vessel) return null;
        const vasePhotoUrl = `${PUBLIC_BASE}/assets/images/heritage/${vessel.id}.png`;
        await sendPhoto(
            fetchWithTimeout,
            zaloBase,
            zaloToken,
            chatId,
            vasePhotoUrl,
            `🏺 Bình #${vessel.num}: ${vessel.name} (${vessel.form})`
        );
        await sendText(
            fetchWithTimeout,
            zaloBase,
            zaloToken,
            chatId,
            `${formatBookBlock(vessel)}\n\n👉 Gõ "sinh ${vessel.num}" để tạo 4 thiết kế áo dài mới từ bình này trên GPU!`
        );
        return { ok: true, mode: 'vessel_detail', heritageId: vessel.id };
    }

    // 3. Sinh thật trên GPU Modal và tự động chờ gửi 4 ảnh khi xong: "sinh 1..6" hoặc "gpu 1..6"
    const genMatch = clean.match(/^(?:sinh|gpu|tao)\s+([1-6]|lr3d_\d+|hv\d+)$/);
    if (genMatch) {
        const ownerId = (process.env.ALERT_ZALO_USER_CHAT_ID || '').trim();
        if (!ownerId || chatId !== ownerId) {
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
                `⏳ Bot sẽ tự động gửi 4 ảnh khi xong. Nếu cần nhận lại, gõ "xem ${job.job_id}".`
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

    // Chỉ đọc đúng job của cuộc trò chuyện; không chọn run mới nhất của người khác.
    const watchMatch = clean.match(/^xem(?:\s+([a-z0-9_-]{1,100}))?$/);
    if (watchMatch) {
        const ownerId = (process.env.ALERT_ZALO_USER_CHAT_ID || '').trim();
        if (!ownerId || chatId !== ownerId) return { ok: true, ignored: 'operator_only' };
        const saved = lastJobByChat.get(chatId);
        const jobId = watchMatch[1] || saved?.jobId;
        if (!jobId) {
            await sendText(fetchWithTimeout, zaloBase, zaloToken, chatId,
                'Chưa có mã lượt sinh trong phiên bot này. Hãy gõ "xem <mã job>" từ tin nhắn bot gửi khi bắt đầu sinh.');
            return { ok: true, mode: 'vessel_watch_missing_job' };
        }
        const config = getBackendConfig();
        try {
            const res = await fetchWithTimeout(
                `${config.modalUrl}/generate/${encodeURIComponent(jobId)}`,
                { headers: buildBackendHeaders('modal', config) },
                config.modalTimeoutMs
            );
            if (res.ok) {
                const job = await res.json();
                const vessel = findVessel(job.heritage_id);
                if (job.status === 'completed' && job.run_id && vessel) {
                    await sendText(
                        fetchWithTimeout,
                        zaloBase,
                        zaloToken,
                        chatId,
                        `${formatBookBlock(vessel)}\n\n✅ Đang gửi ảnh của lượt ${jobId}...`
                    );
                    const urls = [1, 2, 3, 4].map((i) => `${PUBLIC_BASE}/api/live/media/run/${job.run_id}/V${i}_aodai.png`);
                    const sent = await sendFourDesigns(fetchWithTimeout, zaloBase, zaloToken, chatId, vessel, urls, 'Ảnh mới sinh từ GPU');
                    await sendText(fetchWithTimeout, zaloBase, zaloToken, chatId,
                        sent === 4 ? '✅ Đã gửi đủ 4 ảnh.' : `⚠️ Chỉ gửi được ${sent}/4 ảnh. Gõ "xem ${jobId}" để thử lại.`);
                    return { ok: true, mode: 'vessel_watch_completed', runId: job.run_id, sent };
                }
                if (job.status === 'failed') {
                    await sendText(fetchWithTimeout, zaloBase, zaloToken, chatId, `⚠️ Lượt ${jobId} sinh ảnh thất bại.`);
                    return { ok: true, mode: 'vessel_watch_failed' };
                }
            }
        } catch (_) {}
        await sendText(fetchWithTimeout, zaloBase, zaloToken, chatId,
            `⏳ Chưa lấy được kết quả lượt ${jobId}. Nếu GPU còn chạy, hãy thử lại bằng "xem ${jobId}".`);
        return { ok: true, mode: 'vessel_watch_running' };
    }

    return null;
}

module.exports = { tryHandleDesignCommand, VESSELS, formatBookBlock };
