/**
 * bot_ops_commands.js — Bộ lệnh kiểm tra hạ tầng, chi phí, credit & lịch sử cho Zalo Bot.
 * Các lệnh:
 *   - /usage, dung, chi phi: Mức độ sử dụng theo tuần và ngày + ước tính số lượt sinh còn lại.
 *   - /checkcredit, credit, tien: Mức chi AWS Budget đã ghi nhận và đường dẫn Modal Billing.
 *   - /gpu, health, status: Tình trạng cụm GPU T4 (online/idle, cuda, version).
 *   - /runs, lich su: Thống kê số lượt sinh đã thực hiện và 3 lượt mới nhất.
 *   - /menu, help, tro giup: Hướng dẫn danh mục lệnh cho người dùng.
 */

function formatUsageReport(summary, runsCount) {
    const count = Number.isInteger(runsCount) && runsCount >= 0
        ? `Đã ghi nhận ${runsCount} lượt sinh trên backend.`
        : 'Chưa xác minh được số lượt sinh.';
    return `📊 [MỨC SỬ DỤNG]\n${count}\n` +
        'Xem mức chi AWS Budget bằng lệnh "số dư". Credit Modal cần kiểm tra trong Usage & Billing của Modal.';
}

function formatCreditReport(budget) {
    const aws = budget
        ? `AWS Budget toàn tài khoản: đã ghi nhận $${budget.actualUsd.toFixed(2)} / ` +
          `$${budget.limitUsd.toFixed(2)} trong tháng. Dữ liệu AWS có thể cập nhật trễ; ` +
          'Budget chỉ cảnh báo, không khóa chi tiêu.'
        : 'Chưa xác minh được mức chi AWS Budget. Kiểm tra AWS Billing trước khi chạy CodeBuild.';
    return '💳 [CREDIT VÀ CHI PHÍ]\n' + aws + '\n' +
        'Modal Starter chưa cung cấp API báo cáo billing cho bot; xem credit và Spend limit ' +
        'trực tiếp tại Modal → Settings → Usage & Billing: https://modal.com/settings';
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
        let runsCount = null;
        try {
            const rRes = await fetchWithTimeout(`${config.modalUrl}/runs`, {
                headers: buildBackendHeaders('modal', config),
            }, 5000);
            if (rRes.ok) {
                const list = await rRes.json();
                if (Array.isArray(list)) runsCount = list.length;
            }
        } catch (_) {}

        const reply = formatUsageReport(null, runsCount);
        await fetchWithTimeout(`${zaloBase}/bot${zaloToken}/sendMessage`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chat_id: chatId, text: reply }),
        }, 5000).catch(() => {});
        return { ok: true, mode: 'ops_usage' };
    }

    // 3. Kiểm tra credit: /checkcredit, /credit, credit, tien, so du
    if (/^(\/checkcredit|\/credit|checkcredit|credit|so du|con bao nhieu|tien)$/.test(text)) {
        const { readAwsBudget } = require('./aws_budget_client');
        const reply = formatCreditReport(await readAwsBudget());
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
};
