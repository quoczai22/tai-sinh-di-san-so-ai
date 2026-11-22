// Gửi một tin thử tới Discord webhook do người vận hành đặt trong biến môi trường.
const webhook = (process.env.ALERT_DISCORD_WEBHOOK_URL || '').trim();
if (!webhook) {
    console.error('Thiếu ALERT_DISCORD_WEBHOOK_URL.');
    process.exitCode = 1;
} else {
    const time = new Date().toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh' });
    fetch(webhook, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: `Thử cảnh báo Tái Sinh Di Sản Số — ${time} (giờ VN)` }),
    }).then((response) => {
        if (response.ok) console.log('Đã gửi.');
        else { console.error(`Lỗi HTTP ${response.status}.`); process.exitCode = 1; }
    }).catch(() => {
        console.error('Lỗi kết nối.');
        process.exitCode = 1;
    });
}
