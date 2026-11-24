const assert = require('node:assert/strict');
const { notifyAlert, _resetAlertCooldown } = require('../../web_ui/api/_shared');

process.env.ALERT_DISCORD_WEBHOOK_URL = 'https://discord.example.test/webhook';
process.env.ALERT_ZALO_BOT_TOKEN = '';
process.env.ALERT_COOLDOWN_MIN = '30';

(async () => {
    let calls = 0;
    global.fetch = async () => { calls++; return new Response(null, { status: 500 }); };
    _resetAlertCooldown();
    await notifyAlert('test failure');
    await notifyAlert('retry after delivery failure');
    assert.equal(calls, 2, 'failed delivery must not block retry for 30 minutes');

    global.fetch = async () => { calls++; return new Response(null, { status: 204 }); };
    await notifyAlert('delivered');
    await notifyAlert('suppressed after successful delivery');
    assert.equal(calls, 3, 'successful delivery must respect cooldown');
    console.log('alert delivery: HTTP failure can retry; successful delivery respects cooldown');
})().catch((error) => { console.error(error); process.exitCode = 1; });
