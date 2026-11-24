// Gửi một tin thử tới Discord webhook và/hoặc Zalo Bot do người vận hành đặt trong biến môi trường.
const fs = require('node:fs');
const path = require('node:path');
const envFile = path.resolve(__dirname, '../../.env.local');
const hasExplicitEnv = 'ALERT_DISCORD_WEBHOOK_URL' in process.env ||
    'ALERT_ZALO_BOT_TOKEN' in process.env ||
    'ALERT_ZALO_CHAT_ID' in process.env;
if (!hasExplicitEnv && fs.existsSync(envFile)) process.loadEnvFile(envFile);

const webhook = (process.env.ALERT_DISCORD_WEBHOOK_URL || '').trim();
const zaloToken = (process.env.ALERT_ZALO_BOT_TOKEN || '').trim();
const zaloChatId = (process.env.ALERT_ZALO_CHAT_ID || '').trim();
const zaloBase = (process.env.ALERT_ZALO_API_BASE || 'https://bot-api.zapps.me').trim().replace(/\/$/, '');
const hasZalo = Boolean(zaloToken && zaloChatId);

async function main() {
    if (process.argv.includes('--zalo-get-updates')) {
        if (!zaloToken) {
            console.error('Thiếu ALERT_ZALO_BOT_TOKEN để lấy chat_id.');
            process.exitCode = 1;
            return;
        }
        const res = await fetch(`${zaloBase}/bot${zaloToken}/getUpdates`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({}),
        });
        const data = await res.json().catch(() => null);
        const chatId = data?.result?.message?.chat?.id || data?.result?.[0]?.message?.chat?.id || null;
        if (chatId) console.log(`Zalo chat_id: ${chatId}`);
        else console.log('Chưa tìm thấy tin nhắn mới. Hãy nhắn 1 tin bất kỳ cho Bot trên Zalo rồi chạy lại.');
        return;
    }

    if (!webhook && !hasZalo) {
        console.error('Thiếu ALERT_DISCORD_WEBHOOK_URL (hoặc cặp ALERT_ZALO_BOT_TOKEN + ALERT_ZALO_CHAT_ID).');
        process.exitCode = 1;
        return;
    }
    const time = new Date().toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh' });
    const text = `Thử cảnh báo Tái Sinh Di Sản Số — ${time} (giờ VN)`;
    if (webhook) {
        const res = await fetch(webhook, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: text }),
        });
        if (!res.ok) { console.error(`Lỗi HTTP ${res.status}.`); process.exitCode = 1; return; }
    }
    if (hasZalo) {
        const res = await fetch(`${zaloBase}/bot${zaloToken}/sendMessage`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chat_id: zaloChatId, text }),
        });
        if (!res.ok) { console.error(`Lỗi Zalo HTTP ${res.status}.`); process.exitCode = 1; return; }
    }
    console.log('Đã gửi.');
}

main().catch(() => {
    console.error('Lỗi kết nối.');
    process.exitCode = 1;
});
