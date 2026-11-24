const CI_RUNS_URL = 'https://api.github.com/repos/quoczai22/tai-sinh-di-san-so-ai/actions/workflows/modal-backend.yml/runs?branch=main&per_page=1';
const CI_URL = 'https://github.com/quoczai22/tai-sinh-di-san-so-ai/actions/workflows/modal-backend.yml';
const CD_URL = 'https://ap-southeast-2.console.aws.amazon.com/codesuite/codebuild/projects/tai-sinh-di-san-so-ai-modal-deploy/history?region=ap-southeast-2';

async function ciStatusReply(fetchWithTimeout) {
    let ciLine = 'Chưa đọc được trạng thái CI. Mở link GitHub để kiểm tra trực tiếp.';
    try {
        const response = await fetchWithTimeout(CI_RUNS_URL, {
            headers: { Accept: 'application/vnd.github+json', 'User-Agent': 'tai-sinh-di-san-so-ai-bot' },
        }, 6000);
        if (!response.ok) throw new Error(`GitHub HTTP ${response.status}`);
        const runs = (await response.json()).workflow_runs;
        const run = Array.isArray(runs) ? runs[0] : null;
        if (run && run.head_branch === 'main' && /^[0-9a-f]{40}$/.test(run.head_sha || '') &&
            Number.isSafeInteger(run.id)) {
            const result = run.status !== 'completed' ? 'đang chạy'
                : run.conclusion === 'success' ? 'đạt'
                    : run.conclusion === 'failure' ? 'lỗi' : (run.conclusion || 'chưa rõ');
            ciLine = `CI main: ${result} · commit ${run.head_sha.slice(0, 7)}.\n` +
                `Chi tiết: https://github.com/quoczai22/tai-sinh-di-san-so-ai/actions/runs/${run.id}`;
        }
    } catch (_) {
        // A failed status lookup must not be reported as a healthy build.
    }
    return `📋 [CI/CD]\n${ciLine}\nCI: ${CI_URL}\n` +
        `CD Modal: bot không có quyền đọc trạng thái CodeBuild riêng tư. Xem và bấm phát hành tại: ${CD_URL}\n` +
        'Bot không tự deploy hoặc sửa mã.';
}

module.exports = { ciStatusReply };
