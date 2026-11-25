const assert = require('node:assert/strict');
const { readAwsBudget, parseBudgetSnapshot } = require('../../web_ui/lib/aws_budget_client');
const { formatCreditReport, formatUsageReport, parseModalBillingSnapshot } = require('../../web_ui/api/bot_ops_commands');

(async () => {
    const sample = {
        Budget: {
            BudgetName: 'tai-sinh-di-san-so-ai-aws-5usd',
            CalculatedSpend: { ActualSpend: { Amount: '0.42', Unit: 'USD' } },
            BudgetLimit: { Amount: '5', Unit: 'USD' },
        },
    };
    assert.deepEqual(parseBudgetSnapshot(sample), { actualUsd: 0.42, limitUsd: 5 });
    assert.equal(parseBudgetSnapshot({ Budget: { ...sample.Budget, BudgetLimit: null } }), null);
    assert.equal(parseBudgetSnapshot({ Budget: { ...sample.Budget, CalculatedSpend: { ActualSpend: { Amount: null, Unit: 'USD' } } } }), null);

    process.env.AWS_BUDGET_ROLE_ARN = 'arn:aws:iam::879541989575:role/tai-sinh-di-san-so-ai-budget-read';
    const budget = await readAwsBudget(async ({ accountId, roleArn }) => {
        assert.equal(accountId, '879541989575');
        assert.match(roleArn, /budget-read$/);
        return sample;
    });
    assert.deepEqual(budget, { actualUsd: 0.42, limitUsd: 5 });
    assert.match(formatCreditReport(budget), /\$0\.42 \/ \$5\.00/);
    assert.match(formatCreditReport(budget), /cập nhật trễ/);
    assert.match(formatCreditReport(budget), /https:\/\/modal\.com\/settings/);
    assert.match(formatCreditReport(budget), /1️⃣ Modal GPU Backend/);
    assert.match(formatCreditReport(budget), /2️⃣ AWS CodeBuild CD & Parameter Store/);
    assert.doesNotMatch(formatCreditReport(budget), /credit còn lại|100% miễn phí/);

    const modalSample = parseModalBillingSnapshot({
        billing_version: 2,
        metered_cost: 4.04,
        billed_cost: 0,
        credits_applied: 3.99,
        today_cost: 0.12,
        week_cost: 2.5,
        daily: [{ date: '2026-11-25', cost: 0.12 }],
    });
    assert.ok(modalSample);
    const withModal = formatCreditReport(budget, modalSample);
    assert.match(withModal, /\$4\.04/);
    assert.match(withModal, /~\$26\.01/);
    assert.match(withModal, /Số lượt sinh còn lại không thể suy ra chính xác/);
    assert.match(formatUsageReport(modalSample, 28), /\$4\.04/);
    assert.match(formatUsageReport(modalSample, 28), /28 lượt/);
    assert.equal(parseModalBillingSnapshot({ metered_cost: 4.04, billed_cost: 0, credits_applied: 3.99 }).creditsApplied, null);
    assert.equal(parseModalBillingSnapshot({ metered_cost: -1, billed_cost: 0 }), null);

    assert.equal(await readAwsBudget(async () => { throw new Error('AccessDenied'); }), null);
    assert.match(formatCreditReport(null), /Chưa lấy được mức chi AWS Budget/);
    process.env.AWS_BUDGET_ROLE_ARN = '';
    assert.equal(await readAwsBudget(() => { throw new Error('must not call'); }), null);
    console.log('Zalo AWS Budget & Modal Billing: validated data, safe fallback passed');
})().catch((error) => { console.error(error); process.exitCode = 1; });
