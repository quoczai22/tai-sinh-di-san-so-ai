/**
 * bot_ops_commands.js — Bộ lệnh kiểm tra hạ tầng, chi phí, credit & lịch sử cho Zalo Bot.
 * Các lệnh:
 *   - /usage, dung, chi phi: Mức độ sử dụng theo tuần và ngày + ước tính số lượt sinh còn lại.
 *   - /checkcredit, credit, tien: Mức chi AWS Budget đã ghi nhận và đường dẫn Modal Billing.
 *   - /gpu, health, status: Tình trạng cụm GPU T4 (online/idle, cuda, version).
 *   - /runs, lich su: Thống kê số lượt sinh đã thực hiện và 3 lượt mới nhất.
 *   - /menu, help, tro giup: Hướng dẫn danh mục lệnh cho người dùng.
 */

const STARTER_MONTHLY_CREDIT_USD = 30.0;
// Ước tính số lượt còn lại chỉ dựa trên số có nguồn:
//  - Giá GPU T4: $0.000164/giây, niêm yết tại modal.com/pricing (đọc ngày 25/11/2026).
//  - 126,8 giây/lượt: MỘT mẫu đo thật ngày 24/11/2026 (docs/DEPLOY_LIVE.md), container đang ấm.
//  - 420 giây: thời gian giữ máy ấm sau lượt cuối (SCALEDOWN_SECONDS trong modal_app.py), vẫn tính tiền GPU.
// Chưa gồm CPU/RAM (rất nhỏ so với GPU) và chưa đo lúc container nguội.
const T4_USD_PER_SECOND = 0.000164;
const MEASURED_RUN_SECONDS = 126.8;
const WARM_IDLE_SECONDS = 420;

function monthlyCreditAllowance() {
    const configured = Number(process.env.MODAL_MONTHLY_CREDIT);
    return Number.isFinite(configured) && configured > 0 ? configured : STARTER_MONTHLY_CREDIT_USD;
}

function estimateRunRange(remainingUsd) {
    if (!Number.isFinite(remainingUsd) || remainingUsd < 0) return null;
    const runsFor = (seconds) => Math.floor(remainingUsd / (seconds * T4_USD_PER_SECOND));
    return {
        spaced: runsFor(MEASURED_RUN_SECONDS + WARM_IDLE_SECONDS),
        consecutive: runsFor(MEASURED_RUN_SECONDS),
    };
}

function formatRunEstimate(remainingUsd) {
    const range = estimateRunRange(remainingUsd);
    if (!range) return '• Chưa ước tính được số lượt còn lại vì chưa xác minh credit còn lại.';
    const fmt = (n) => n.toLocaleString('vi-VN');
    return `• Ước tính còn chạy được: ~${fmt(range.spaced)} – ${fmt(range.consecutive)} lượt sinh GPU T4.\n` +
        `   (${fmt(range.spaced)}: mỗi lượt cách nhau hơn 7 phút, tính cả thời gian giữ máy ấm; ` +
        `${fmt(range.consecutive)}: chạy liên tiếp. Dựa trên giá T4 $${T4_USD_PER_SECOND}/giây × ` +
        `${String(MEASURED_RUN_SECONDS).replace('.', ',')} giây/lượt, mới đo 1 mẫu; chưa gồm CPU/RAM.)`;
}

function parseModalBillingSnapshot(data) {
    if (!data || typeof data !== 'object') return null;
    const meteredCost = Number(data.metered_cost);
    const billedCost = Number(data.billed_cost);
    if (!Number.isFinite(meteredCost) || meteredCost < 0) return null;
    if (!Number.isFinite(billedCost) || billedCost < 0) return null;
    const creditsApplied = data.billing_version === 2 && data.credits_applied != null &&
        Number.isFinite(Number(data.credits_applied)) && Number(data.credits_applied) >= 0
        ? Number(data.credits_applied) : null;
    const todayCost = data.today_cost != null && Number.isFinite(Number(data.today_cost)) ? Number(data.today_cost) : null;
    const weekCost = data.week_cost != null && Number.isFinite(Number(data.week_cost)) ? Number(data.week_cost) : null;
    const daily = Array.isArray(data.daily)
        ? data.daily
            .filter((d) => d && typeof d.date === 'string' && Number.isFinite(Number(d.cost)))
            .map((d) => ({ date: d.date, cost: Number(d.cost) }))
        : [];
    return { meteredCost, billedCost, creditsApplied, todayCost, weekCost, daily };
}

async function readModalBilling(fetchWithTimeout, config, buildBackendHeaders) {
    const billingUrl = (
        config?.modalBillingUrl ||
        (config?.modalUrl && config.modalUrl.includes('-fastapi-app.')
            ? config.modalUrl.replace('-fastapi-app.', '-billing-summary.')
            : '')
    ).trim().replace(/\/$/, '');
    if (!billingUrl || !config?.modalKey) return null;
    try {
        const res = await fetchWithTimeout(`${billingUrl}/summary`, {
            headers: buildBackendHeaders('modal', config),
        }, 10000);
        if (!res.ok) return null;
        return parseModalBillingSnapshot(await res.json());
    } catch (_) {
        return null;
    }
}

function formatUsageReport(summary, runsCount) {
    const count = Number.isInteger(runsCount) && runsCount >= 0
        ? `• Đã ghi nhận ${runsCount} lượt sinh trên backend.`
        : '• Chưa xác minh được số lượt sinh.';
    if (!summary) {
        return `📊 [MỨC SỬ DỤNG]\n${count}\n` +
            'Xem mức chi AWS Budget bằng lệnh "số dư". Credit Modal cần kiểm tra trong Usage & Billing của Modal.';
    }
    const allowance = monthlyCreditAllowance();
    const remaining = summary.creditsApplied === null ? null : Math.max(0, allowance - summary.creditsApplied);
    const dailyLines = [];
    if (summary.todayCost !== null) dailyLines.push(`• Hôm nay: $${summary.todayCost.toFixed(4)}`);
    if (summary.weekCost !== null) dailyLines.push(`• 7 ngày qua: $${summary.weekCost.toFixed(2)}`);
    if (summary.daily.length > 0) {
        const recent = summary.daily
            .map((d) => `${d.date.slice(5).split('-').reverse().join('/')} ($${d.cost.toFixed(2)})`)
            .join(', ');
        dailyLines.push(`• Các ngày gần nhất: ${recent}`);
    }
    return '📊 [MỨC SỬ DỤNG MODAL GPU]\n\n' +
        (dailyLines.length ? `📅 Theo ngày & tuần (số liệu thật):\n${dailyLines.join('\n')}\n\n` : '') +
        '💳 Tháng này (số liệu thật từ Modal):\n' +
        `• Đã tiêu dùng: $${summary.meteredCost.toFixed(2)}\n` +
        `• Hóa đơn thực tế: $${summary.billedCost.toFixed(2)}\n` +
        `• Credit đã áp dụng: ${summary.creditsApplied === null ? 'chưa xác minh' : `$${summary.creditsApplied.toFixed(2)}`}\n` +
        `• Credit gói Starter còn lại (ước tính từ $${allowance.toFixed(2)}): ${remaining === null ? 'chưa xác minh' : `~$${remaining.toFixed(2)}`}\n\n` +
        '🎯 Lượt sinh:\n' +
        `${count}\n` +
        formatRunEstimate(remaining);
}

function formatCreditReport(budget, modalBilling = null) {
    const allowance = monthlyCreditAllowance();
    let modalSection;
    if (modalBilling) {
        const remaining = modalBilling.creditsApplied === null ? null : Math.max(0, allowance - modalBilling.creditsApplied);
        modalSection =
            `• Hạn mức gói Starter: $${allowance.toFixed(2)} / tháng\n` +
            `• Đã tiêu dùng (thực tế): $${modalBilling.meteredCost.toFixed(2)}\n` +
            `• Credit đã áp dụng: ${modalBilling.creditsApplied === null ? 'chưa xác minh' : `$${modalBilling.creditsApplied.toFixed(2)}`}\n` +
            `• Credit gói Starter còn lại (ước tính): ${remaining === null ? 'chưa xác minh' : `~$${remaining.toFixed(2)}`}\n` +
            `• Hóa đơn thực tế: $${modalBilling.billedCost.toFixed(2)}\n` +
            `🎯 ${formatRunEstimate(remaining).replace(/^• /, '')}`;
    } else {
        modalSection =
            '• Credit, mức đã dùng và Spend limit: bot chưa đọc được từ Modal.\n' +
            '• Xem số liệu hiện tại: https://modal.com/settings\n' +
            '• Không ước tính số lượt sinh còn lại khi thiếu số liệu GPU thực tế.';
    }
    const aws = budget
        ? `• Chi phí AWS đã ghi nhận: $${budget.actualUsd.toFixed(2)} / ` +
          `$${budget.limitUsd.toFixed(2)} Budget tháng này.\n` +
          '• Budget cảnh báo khi chạm ngưỡng, không khóa cứng chi tiêu. Dữ liệu có thể cập nhật trễ.'
        : '• Chưa lấy được mức chi AWS Budget; hãy kiểm tra AWS Billing trước khi chạy CodeBuild.';
    return '💳 [KIỂM TRA HẠN MỨC & CREDIT HỆ THỐNG]\n\n' +
        '1️⃣ Modal GPU Backend:\n' + modalSection + '\n\n' +
        '2️⃣ AWS CodeBuild CD & Parameter Store:\n' + aws + '\n' +
        '• Phút CodeBuild đã dùng/còn lại: chưa kết nối dữ liệu sử dụng; xem trong AWS Billing.\n' +
        '• Token CD lưu trong Parameter Store SecureString; bot không đọc giá trị token.';
}

function formatGpuStatus(health, elapsedMs, failure) {
    if (!health) {
        return (
            '🟡 [TRẠNG THÁI GPU MODAL]\n\n' +
            `• Chưa xác minh được GPU: ${failure || 'không có phản hồi hợp lệ'}.\n` +
            `• Thời gian kiểm tra: ${elapsedMs}ms.\n` +
            '• Chưa nên kết luận GPU đang ngủ hoặc sẵn sàng sinh ảnh. Hãy thử lại sau khi Modal khởi động.'
        );
    }
    return (
        `${health.cuda && health.generation_available ? '🟢' : '🟡'} [TRẠNG THÁI GPU MODAL · ĐÃ PHẢN HỒI]\n\n` +
        `• Thiết bị: ${health.device || 'chưa xác định'}\n` +
        `• CUDA: ${health.cuda ? 'Khả dụng' : 'Chưa bật'}\n` +
        `• Phiên bản Backend: ${health.version || 'chưa xác định'}\n` +
        `• Trạng thái sinh ảnh: ${health.generation_available ? 'Sẵn sàng tiếp nhận' : 'Bận'}\n` +
        `• Độ trễ phản hồi: ${elapsedMs}ms`
    );
}

function formatRunsHistory(runs) {
    if (!Array.isArray(runs)) {
        return '📜 [LỊCH SỬ SINH ẢNH]\nKhông kết nối được Modal; chưa xác minh được lịch sử.';
    }
    if (runs.length === 0) {
        return '📜 [LỊCH SỬ SINH ẢNH]\nChưa có lượt sinh ảnh nào được ghi nhận trên Volume.';
    }
    const latest = runs.slice(-3).reverse();
    const itemsText = latest.map((r, i) => {
        const time = r.created_at ? new Date(r.created_at).toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh' }) : 'Vừa xong';
        return `${i + 1}. Bình ${r.code || r.heritage_id} · ${r.designs || 4} ảnh · ${time}`;
    }).join('\n');

    return (
        `📜 [LỊCH SỬ SINH ẢNH GPU]\n\n` +
        `• Tổng số lượt sinh đã hoàn tất: ${runs.length} lượt\n\n` +
        `🕒 3 lượt gần nhất:\n${itemsText}\n\n` +
        '👉 Gõ "xem" để nhận lại ảnh của lượt sinh gắn với cuộc trò chuyện này (nếu còn mã job).'
    );
}

function formatDeployInstructions() {
    return (
        '🚀 [QUY TRÌNH TRIỂN KHAI CD TỰ ĐỘNG · AWS CODEBUILD]\n\n' +
        '1️⃣ Kiểm tra chất lượng (CI Main):\n' +
        '• Link GitHub Actions: https://github.com/quoczai22/tai-sinh-di-san-so-ai/actions\n' +
        '• Đảm bảo commit trên nhánh "main" đã chạy qua 100% test case kiểm thử.\n\n' +
        '2️⃣ Triển khai tự động lên Modal GPU (CD):\n' +
        '• Vào AWS CodeBuild Console: https://ap-southeast-2.console.aws.amazon.com/codesuite/codebuild/projects/tai-sinh-di-san-so-ai-modal-deploy/history?region=ap-southeast-2\n' +
        '• Bấm nút: [ Start build ]\n' +
        '• Hệ thống AWS CodeBuild sẽ tự động lấy Token CD bảo mật từ Parameter Store và deploy code mới lên Modal mà không lộ khóa ra ngoài!\n\n' +
        '💳 Hạn mức AWS CodeBuild:\n' +
        '• Xem mức dùng và chi phí thực tế trong AWS Billing trước khi deploy.\n' +
        '• Parameter Store Token CD: Miễn phí hoàn toàn (Standard Tier).\n\n' +
        '🔒 Lưu ý bảo mật: Bot chỉ là giao diện giám sát & thông báo, quyền bấm deploy cuối cùng thuộc về người vận hành trên AWS Console.'
    );
}

function formatHelpMenu() {
    return (
        '📖 [DANH MỤC LỆNH BOT TÁI SINH DI SẢN SỐ]\n\n' +
        '🏺 Trải nghiệm hiện vật & Áo dài:\n' +
        '• "1" .. "6" / "bình 1" .. "bình 6": Xem ảnh bình gốm thật + mở Sổ hoa văn.\n' +
        '• "sinh 1" .. "sinh 6": Gọi GPU Modal T4 sinh mới 4 ảnh áo dài và tự động gửi vào Zalo.\n' +
        '• "xem": Nhận lại 4 ảnh áo dài vừa sinh gần nhất từ GPU.\n\n' +
        '⚙️ Quản trị & Giám sát hệ thống (Song ngữ Anh - Việt):\n' +
        '• /usage (hoặc "mức dùng", "chi phí", "tiêu thụ"): Xem số lượt đã ghi nhận; chi phí cần kiểm tra trong Billing.\n' +
        '• /checkcredit (hoặc "số dư", "tiền", "credit"): Xem mức chi AWS Budget và đường dẫn kiểm tra Modal.\n' +
        '• /gpu (hoặc "trạng thái", "thiết bị", "phần cứng"): Kiểm tra tình trạng cụm GPU T4 (online/idle).\n' +
        '• /runs (hoặc "lịch sử", "danh sách sinh"): Xem tổng số lượt sinh và 3 lượt mới nhất.\n' +
        '• /deploy (hoặc "triển khai", "phát hành", "/cd"): Hướng dẫn & link triển khai AWS CodeBuild CD.'
    );
}

async function tryHandleOpsCommand({
    cleanText,
    chatId,
    zaloBase,
    zaloToken,
    fetchWithTimeout,
    getBackendConfig,
    buildBackendHeaders,
}) {
    const text = cleanText.toLowerCase();

    // 1. Menu trợ giúp: /menu, /help, menu, giup, tro giup, lenh
    if (/^(\/menu|\/help|menu|help|tro giup|huong dan|danh muc|lenh)$/.test(text)) {
        await fetchWithTimeout(`${zaloBase}/bot${zaloToken}/sendMessage`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chat_id: chatId, text: formatHelpMenu() }),
        }, 5000).catch(() => {});
        return { ok: true, mode: 'ops_menu' };
    }

    // 2. Kiểm tra mức dùng /usage: /usage, usage, muc dung, chi phi, da dung
    if (/^(\/usage|usage|muc dung|chi phi|da dung|tieu thu)$/.test(text)) {
        const config = getBackendConfig();
        const [runsCount, modalBilling] = await Promise.all([
            (async () => {
                try {
                    const rRes = await fetchWithTimeout(`${config.modalUrl}/runs`, {
                        headers: buildBackendHeaders('modal', config),
                    }, 5000);
                    if (rRes.ok) {
                        const list = await rRes.json();
                        if (Array.isArray(list)) return list.length;
                    }
                } catch (_) {}
                return null;
            })(),
            readModalBilling(fetchWithTimeout, config, buildBackendHeaders),
        ]);

        const reply = formatUsageReport(modalBilling, runsCount);
        await fetchWithTimeout(`${zaloBase}/bot${zaloToken}/sendMessage`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chat_id: chatId, text: reply }),
        }, 5000).catch(() => {});
        return { ok: true, mode: 'ops_usage' };
    }

    // 3. Kiểm tra credit: /checkcredit, /credit, credit, tien, so du
    if (/^(\/checkcredit|\/credit|checkcredit|credit|so du|con bao nhieu|tien)$/.test(text)) {
        const { readAwsBudget } = require('../lib/aws_budget_client');
        const config = getBackendConfig();
        const [budget, modalBilling] = await Promise.all([
            readAwsBudget(),
            readModalBilling(fetchWithTimeout, config, buildBackendHeaders),
        ]);
        const reply = formatCreditReport(budget, modalBilling);
        await fetchWithTimeout(`${zaloBase}/bot${zaloToken}/sendMessage`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chat_id: chatId, text: reply }),
        }, 5000).catch(() => {});
        return { ok: true, mode: 'ops_credit' };
    }

    // 4. Kiểm tra GPU: /gpu, gpu, phan cung, t4, cuda
    if (/^(\/gpu|gpu|t4|cuda|thiet bi)$/.test(text)) {
        const config = getBackendConfig();
        const t0 = Date.now();
        let health = null;
        let failure = '';
        try {
            if (!config.modalUrl || !config.modalKey) {
                failure = 'thiếu MODAL_URL hoặc MODAL_KEY trên Vercel';
            } else {
                const hRes = await fetchWithTimeout(`${config.modalUrl}/health`, {
                    headers: buildBackendHeaders('modal', config),
                }, Math.min(50000, Math.max(20000, config.modalTimeoutMs)));
                if (hRes.ok) health = await hRes.json();
                else failure = `Modal trả HTTP ${hRes.status}`;
            }
        } catch (error) {
            failure = error.name === 'AbortError' || /timeout/i.test(error.message)
                ? 'quá thời gian chờ Modal khởi động'
                : 'lỗi kết nối tới Modal';
        }
        const elapsedMs = Date.now() - t0;
        const reply = formatGpuStatus(health, elapsedMs, failure);
        await fetchWithTimeout(`${zaloBase}/bot${zaloToken}/sendMessage`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chat_id: chatId, text: reply }),
        }, 5000).catch(() => {});
        return { ok: true, mode: 'ops_gpu' };
    }

    // 5. Kiểm tra lịch sử runs: /runs, runs, lich su, danh sach sinh, cac luot sinh
    if (/^(\/runs|runs|lich su|danh sach sinh|cac luot sinh|lich|nhat ky)$/.test(text)) {
        const config = getBackendConfig();
        let runs = null;
        try {
            const rRes = await fetchWithTimeout(`${config.modalUrl}/runs`, {
                headers: buildBackendHeaders('modal', config),
            }, 6000);
            if (rRes.ok) runs = await rRes.json();
        } catch (_) {}
        const reply = formatRunsHistory(runs);
        await fetchWithTimeout(`${zaloBase}/bot${zaloToken}/sendMessage`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chat_id: chatId, text: reply }),
        }, 5000).catch(() => {});
        return { ok: true, mode: 'ops_runs' };
    }

    // 6. Hướng dẫn & link triển khai CD: /deploy, /cd, deploy, phat hanh, trien khai, cd
    if (/^(\/deploy|\/cd|deploy|phat hanh|trien khai|cd)$/.test(text)) {
        const reply = formatDeployInstructions();
        await fetchWithTimeout(`${zaloBase}/bot${zaloToken}/sendMessage`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chat_id: chatId, text: reply }),
        }, 5000).catch(() => {});
        return { ok: true, mode: 'ops_deploy' };
    }

    return null;
}

module.exports = {
    tryHandleOpsCommand,
    formatUsageReport,
    formatCreditReport,
    formatGpuStatus,
    formatRunsHistory,
    formatHelpMenu,
    parseModalBillingSnapshot,
    readModalBilling,
    estimateRunRange,
};
