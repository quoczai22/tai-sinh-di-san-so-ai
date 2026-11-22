const PUBLIC_BASE = 'https://tai-sinh-di-san-so-ai.vercel.app';

const VESSELS = [
    { num: 1, id: 'LR3D_33', code: 'HV07', name: 'Huy hiệu, mẫu đơn và dây sen' },
    { num: 2, id: 'LR3D_61', code: 'HV08', name: 'Rồng và mây' },
    { num: 3, id: 'LR3D_50', code: 'HV09', name: 'Dây hoa cuộn dày' },
    { num: 4, id: 'LR3D_38', code: 'HV10', name: 'Cây hoa' },
    { num: 5, id: 'LR3D_97', code: 'HV11', name: 'Nét lam thưa trên men kem' },
    { num: 6, id: 'LR3D_124', code: 'HV12', name: 'Huy hiệu rồng' },
];

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
            `${prefixLabel} · Thiết kế ${i + 1}/4 — Bình #${vessel.num}: ${vessel.name} (${vessel.id})`
        );
    }
}

async function tryHandleDesignCommand({
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
    if (chatType !== 'PRIVATE') return null;

    const clean = normalizedText.trim();

    // 1. Danh sách bình: "binh", "danh sach", "menu", "chon binh"
    if (/^(binh|danh sach( binh)?|chon binh|menu|test binh)$/.test(clean)) {
        const lines = VESSELS.map((v) => `${v.num}. ${v.name} (${v.id})`).join('\n');
        const msg = `🏺 Danh sách 6 bình gốm Bát Tràng:\n${lines}\n\n` +
            '👉 Gõ "bình 1" .. "bình 6" (hoặc số 1..6): Nhận ngay 4 ảnh áo dài của bình đó.\n' +
            '👉 Gõ "sinh 1" .. "sinh 6": Gọi GPU Modal T4 sinh mới 4 ảnh áo dài thật.\n' +
            '👉 Gõ "xem": Kiểm tra tiến độ và nhận 4 ảnh GPU vừa sinh xong.';
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
            `🏺 Bình #${vessel.num}: ${vessel.name} (${vessel.id})\nĐang gửi 4 thiết kế áo dài vào Zalo của bạn...`
        );
        const urls = [1, 2, 3, 4].map((i) => `${PUBLIC_BASE}/assets/images/variants/${vessel.id}_V${i}_aodai.png`);
        await sendFourDesigns(fetchWithTimeout, zaloBase, zaloToken, chatId, vessel, urls, 'Áo dài');
        return { ok: true, mode: 'vessel_preview', heritageId: vessel.id };
    }

    // 3. Sinh thật trên GPU Modal: "sinh 1..6" hoặc "gpu 1..6"
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
                `🎨 Đã bắt đầu sinh 4 thiết kế mới trên GPU T4 cho Bình #${vessel.num}: ${vessel.name} (${vessel.id}).\n` +
                `Mã lượt: ${job.job_id}\n` +
                `⏳ Sau khoảng 60–90 giây, bạn nhắn:\nxem ${vessel.num} ${job.job_id}\n(hoặc chỉ cần gõ "xem") để nhận 4 ảnh PNG vừa sinh!`
            );
            return { ok: true, mode: 'vessel_generate_started', heritageId: vessel.id, jobId: job.job_id };
        } catch (_) {
            await sendText(fetchWithTimeout, zaloBase, zaloToken, chatId, '⚠️ Modal GPU đang khởi động chậm hoặc lỗi kết nối. Bạn thử lại sau ít giây nhé.');
            return { ok: true, mode: 'vessel_generate_error' };
        }
    }

    // 4. Kiểm tra và nhận 4 ảnh vừa sinh: "xem" hoặc "xem <num> <jobId>"
    const watchMatch = clean.match(/^xem(?:\s+([1-6]|lr3d_\d+)\s+([a-z0-9_-]+))?$/) ||
        clean.match(/^xem\s+([a-z0-9_-]{16,})$/);
    if (watchMatch) {
        const saved = lastJobByChat.get(chatId);
        let vessel = saved?.vessel || VESSELS[1];
        let jobId = saved?.jobId || '';
        if (watchMatch[2]) {
            vessel = findVessel(watchMatch[1]) || vessel;
            jobId = watchMatch[2];
        } else if (watchMatch[1] && watchMatch[1].length >= 16) {
            jobId = watchMatch[1];
        }
        if (!jobId) {
            await sendText(
                fetchWithTimeout,
                zaloBase,
                zaloToken,
                chatId,
                'Hiện chưa có lượt sinh GPU nào đang chờ. Bạn gõ "bình 1".."bình 6" để xem ngay 4 ảnh, hoặc "sinh 1".."sinh 6" để gọi GPU sinh mới nhé!'
            );
            return { ok: true, mode: 'vessel_watch_empty' };
        }
        const config = getBackendConfig();
        try {
            const res = await fetchWithTimeout(
                `${config.modalUrl}/generate/${encodeURIComponent(jobId)}`,
                { headers: buildBackendHeaders('modal', config) },
                config.modalTimeoutMs
            );
            if (!res.ok) {
                await sendText(fetchWithTimeout, zaloBase, zaloToken, chatId, `⚠️ Không đọc được trạng thái job ${jobId} (HTTP ${res.status}).`);
                return { ok: true, mode: 'vessel_watch_error' };
            }
            const job = await res.json();
            if (['queued', 'running'].includes(job.status)) {
                await sendText(
                    fetchWithTimeout,
                    zaloBase,
                    zaloToken,
                    chatId,
                    `⏳ GPU T4 đang sinh cho ${vessel.name}: ${job.progress || 0}% (${job.label || 'đang chạy'}).\nBạn đợi thêm ít giây rồi gõ lại "xem" nhé!`
                );
                return { ok: true, mode: 'vessel_watch_running', progress: job.progress || 0 };
            }
            if (job.status !== 'completed' || !job.run_id) {
                await sendText(fetchWithTimeout, zaloBase, zaloToken, chatId, `⚠️ Lượt sinh kết thúc với trạng thái: ${job.status} (${job.label || ''}).`);
                return { ok: true, mode: 'vessel_watch_failed' };
            }
            await sendText(
                fetchWithTimeout,
                zaloBase,
                zaloToken,
                chatId,
                `✅ Đã sinh xong 4/4 thiết kế mới trên GPU T4 (Run: ${job.run_id})! Đang gửi 4 ảnh vào Zalo...`
            );
            const urls = [1, 2, 3, 4].map((i) => `${PUBLIC_BASE}/api/live/media/run/${job.run_id}/V${i}_aodai.png`);
            await sendFourDesigns(fetchWithTimeout, zaloBase, zaloToken, chatId, vessel, urls, `GPU Run ${job.run_id}`);
            return { ok: true, mode: 'vessel_watch_completed', runId: job.run_id };
        } catch (_) {
            await sendText(fetchWithTimeout, zaloBase, zaloToken, chatId, '⚠️ Chưa kết nối được Modal để lấy trạng thái job. Bạn thử gõ lại "xem" sau vài giây nhé.');
            return { ok: true, mode: 'vessel_watch_error' };
        }
    }

    return null;
}

module.exports = { tryHandleDesignCommand, VESSELS };
